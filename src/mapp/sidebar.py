import base64
import io
import math
import os.path
import pickle
from io import BytesIO

import numpy as np
from PIL import Image
from webapp_client.components import Div, FileUpload, Row
from webapp_client.qcomponents import QBtn, QCheckbox, QSlider, QTooltip
from webgpu import platform


def image_to_data_uri(image: Image.Image) -> str:
    """Convert a PIL image to a data URI (webp format)."""
    buffer = BytesIO()
    image.save(buffer, format="WEBP")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/webp;base64,{encoded}"


class LayerOptions(Div):
    def __init__(self, openlayers, name="", layer=None, **kwargs):
        super().__init__(**kwargs, namespace=True)
        self.openlayers = openlayers
        self.layer = layer
        self.opacity = QSlider(
            ui_model_value=1.0,
            ui_min=0.0,
            ui_max=1.0,
            ui_step=0.01,
            ui_dense=True,
            ui_style={"max-width": "150px"},
            ui_class="q-pt-sm",
            id="opacity",
        )
        self.visible = QCheckbox(
            ui_model_value=True, id="visible"
        ).on_update_model_value(self.set_visible)
        self.name_div = Div(name, id="name", ui_style="width: 6em", ui_class="q-pt-sm")
        self.opacity.on_update_model_value(self.set_opacity)
        self.ui_children = [Row(self.visible, self.name_div, self.opacity)]

    def set_opacity(self, event):
        self.layer.setOpacity(event.value["value"])

    def set_visible(self, event):
        self.layer.setVisible(event.value["value"])

    def update_ol(self):
        self.layer.setOpacity(self.opacity.ui_model_value)
        self.layer.setVisible(self.visible.ui_model_value)


class ImageLayer(LayerOptions):
    def __init__(self, openlayers, name, **kwargs):
        self.name = name
        self.align_btn = QBtn(
            ui_icon="mdi-move-resize",
            ui_color="primary",
            ui_class="q-ml-md",
        ).on_click(self.set_alignment)
        layer = platform.js.ol.layer.Image._new(
            {
                "opacity": 0.8,
            }
        )
        self.tooltip = QTooltip("")
        super().__init__(openlayers, name, layer, **kwargs)
        self.opacity.ui_model_value = 0.8
        self.ui_children = [
            Row(self.visible, self.name_div, self.opacity, self.align_btn, self.tooltip)
        ]

        self.points = []

    def set_alignment(self):
        self.points = []
        self._one_click_callback(self._on_click_align)
        self.tooltip.ui_children = ["Click on first point on image to align"]
        self.tooltip.ui_show()

    def _one_click_callback(self, f):
        olmap = self.openlayers.olmap

        def func(event):
            return f(event)

        func.ol_key = None
        olmap.once("click", func)

    def _on_click_align(self, event):
        ol = platform.js.ol
        coord = event.coordinate
        coord = ol.proj.fromLonLat(event.coordinate)
        self.points.append(np.array(coord))

        if len(self.points) < 4:
            self._one_click_callback(self._on_click_align)
            if len(self.points) in [1, 3]:
                self.tooltip.ui_children = ["Click on corresponding point on the map"]
            else:
                self.tooltip.ui_children = ["Click on second point on image to align"]
            self.tooltip.ui_show()
            return

        self.tooltip.ui_children = []
        self.tooltip.ui_hide()

        p = self.points
        p0 = p[0]
        p = [pi - p0 for pi in p]

        v_src = p[2] - p[0]
        v_dst = p[3] - p[1]

        scale = np.linalg.norm(v_dst) / np.linalg.norm(v_src)
        angle = math.atan2(v_dst[1], v_dst[0]) - math.atan2(v_src[1], v_src[0])

        rotmat = np.array(
            [
                [math.cos(angle), -math.sin(angle)],
                [math.sin(angle), math.cos(angle)],
            ]
        )
        new_p0 = rotmat @ p[0] * scale
        t = p[1] - new_p0
        angle_deg = math.degrees(angle)

        def f(x):
            return rotmat @ (x - p0) * scale + t + p0

        x0, y0, x1, y1 = self.storage.get("extent")
        x_range = []
        y_range = []
        for ex in [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]:
            x, y = f(np.array(ex))
            x_range.append(x)
            y_range.append(y)

        new_extent = [min(x_range), min(y_range), max(x_range), max(y_range)]
        new_extent = [float(x) for x in new_extent]
        self.img = self.img.rotate(angle_deg, expand=True)
        self.set_source(self.img, new_extent)
        self.points = []

    def set_source(self, img, extent):
        self.img = img
        ol = platform.js.ol
        source = ol.source.ImageStatic._new(
            {
                "url": image_to_data_uri(img),
                "projection": "EPSG:3857",
                "imageExtent": extent,
            }
        )
        self.storage.set("image", img, use_pickle=True)
        self.storage.set("extent", extent)
        self.layer.setSource(source)

    def load(self, data):
        super().load(data)
        image = self.storage.get("image")
        extent = self.storage.get("extent")
        if image:
            self.set_source(image, extent)
            self.openlayers.olmap.addLayer(self.layer)


class SidebarComponent(Div):
    def __init__(self, openlayers, **kwargs):
        self.openlayers = openlayers
        self.save_btn = QBtn(
            ui_icon="save",
            ui_color="primary",
        ).on_click(self.save_all)
        self.load_btn = QBtn(
            ui_icon="mdi-folder-open",
            ui_color="primary",
        ).on_click(self.load_all)
        self.map_upload = FileUpload(
            id="file_upload",
            ui_label="Upload map file",
            ui_accept=".png,.jpg,.jpeg,.webp,.bmp",
            ui_error_title="Error in Map Upload",
            ui_error_message="Please upload an Image file (png, jpg, jpeg, webp, bmp).",
        ).on_update_model_value(self.upload_layer)
        self.div_layers = Div(id="div_layers")
        self.image_layers = []
        super().__init__(
            self.save_btn, self.load_btn, self.div_layers, self.map_upload, **kwargs
        )

    def save_all(self):
        app = self._status.app
        app.component._emit_recursive("before_save")
        data = app.dump(include_storage_data=True)
        layer_names = [layer.name for layer in self.image_layers]
        import pyodide.ffi
        from pyodide_js import FS

        if not os.path.exists("/data"):
            FS.mkdir("/data")
            FS.mount(FS.filesystems.IDBFS, {"autoPersist": True}, "/data")
        pickle.dump((layer_names, data), open("/data/webapp_mapp_data", "wb"))

        def done(*args):
            pass

        FS.syncfs(pyodide.ffi.create_once_callable(done))

    def load_all(self):
        import pyodide.ffi
        from pyodide_js import FS

        def do_load(*args):
            if not os.path.exists("/data/webapp_mapp_data"):
                return
            app = self._status.app
            layer_names, data = pickle.load(open("/data/webapp_mapp_data", "rb"))
            layers = []
            for name in layer_names:
                layers.append(ImageLayer(self.openlayers, name, id="layer_" + name))
            self.image_layers = layers
            self.div_layers.ui_children = self.div_layers.ui_children + layers
            app.load(data)
            for layer in self.div_layers.ui_children:
                layer.update_ol()

        if not os.path.exists("/data"):
            FS.mkdir("/data")
            FS.mount(FS.filesystems.IDBFS, {"autoPersist": True}, "/data")
        FS.syncfs(True, pyodide.ffi.create_once_callable(do_load))

    def dump(self):
        return super().dump() | {"n_layers": len(self.image_layers)}

    def build_inputs(self, layers):
        children = []

        for name in layers:
            children.append(
                LayerOptions(self.openlayers, name, layers[name], id="layer_" + name)
            )

        self.div_layers.ui_children = children

    def upload_layer(self):
        olmap = self.openlayers.olmap
        from webgpu.platform import js

        state = olmap.frameState_
        extent = state["extent"]
        x0, y0, x1, y1 = extent

        name = self.map_upload.filename
        data = self.map_upload.storage.get(name)
        self.map_upload.storage.delete(name)
        name = name.split(".")[0]
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        self.map_upload.clear_file()
        aspect = img.size[0] / img.size[1]

        y1 = y0 + (x1 - x0) / aspect
        self.add_layer(name, img, [x0, y0, x1, y1])

    def add_layer(self, name, img, extent):
        olmap = self.openlayers.olmap
        imlayer = ImageLayer(self.openlayers, name, id="layer_" + name)
        self.div_layers.ui_children = self.div_layers.ui_children + [
            imlayer,
        ]
        imlayer.set_source(img, extent)

        olmap.addLayer(imlayer.layer)
        self.image_layers.append(imlayer)
