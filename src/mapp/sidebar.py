import base64
import io
import math
from io import BytesIO

import numpy as np
from PIL import Image
from webapp_client.components import Col, Div, FileUpload, Row
from webapp_client.qcomponents import QBtn, QCheckbox, QSlider
from webgpu import platform


def compute_similarity_transform(points):
    """
    Compute 2D similarity transform (rotation, uniform scale, translation)
    from two source and two destination points.

    Returns: 2x3 matrix [[a, -b, tx], [b, a, ty]] where:
        [a, -b] = s * rotation matrix
    """
    # Convert to numpy
    p1_src, p1_dst, p2_src, p2_dst = points
    p1_src = np.array(p1_src)
    p2_src = np.array(p2_src)
    p1_dst = np.array(p1_dst)
    p2_dst = np.array(p2_dst)

    # Vectors before and after
    v_src = p2_src - p1_src
    v_dst = p2_dst - p1_dst

    # Compute scale (isometric)
    len_src = np.linalg.norm(v_src)
    len_dst = np.linalg.norm(v_dst)
    if len_src == 0 or len_dst == 0:
        raise ValueError("Source or destination points are identical.")
    scale = len_dst / len_src

    # Compute angle
    angle = math.atan2(v_dst[1], v_dst[0]) - math.atan2(v_src[1], v_src[0])
    cos_theta = math.cos(angle)
    sin_theta = math.sin(angle)

    # Compute transformation matrix components
    a = scale * cos_theta
    b = scale * sin_theta

    # Compute translation
    tx = p1_dst[0] - a * p1_src[0] + b * p1_src[1]
    ty = p1_dst[1] - b * p1_src[0] - a * p1_src[1]

    angle_deg = math.degrees(angle)

    def f(x, y):
        return a * x - b * y + tx, b * x + a * y + ty

    return angle_deg, f


def image_to_data_uri(image: Image.Image) -> str:
    """Convert a PIL image to a data URI (webp format)."""
    buffer = BytesIO()
    image.save(buffer, format="WEBP")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/webp;base64,{encoded}"


class LayerOptions(Div):
    def __init__(self, openlayers, name, layer, **kwargs):
        super().__init__(**kwargs)
        self.openlayers = openlayers
        self.layer = layer
        self.opacity = QSlider(
            ui_model_value=1.0,
            ui_min=0.0,
            ui_max=1.0,
            ui_step=0.01,
            ui_dense=True,
            ui_style={"max-width": "100px"},
            ui_class="q-pt-sm",
        )
        self.visible = QCheckbox(ui_model_value=True).on_update_model_value(
            self.set_visible
        )
        self.name_div = Div(name, ui_style="width: 6em", ui_class="q-pt-sm")
        self.opacity.on_update_model_value(self.set_opacity)
        self.ui_children = [Row(self.visible, self.name_div, self.opacity)]

    def set_opacity(self, event):
        self.layer._call_method("setOpacity", [event.value["value"]])

    def set_visible(self, event):
        self.layer._call_method("setVisible", [event.value["value"]])


class ImageLayer(LayerOptions):
    def __init__(self, openlayers, name, *args, **kwargs):
        self.align_btn = QBtn(
            ui_icon="align_horizontal_left", ui_color="primary", ui_class="q-ml-md"
        ).on_click(self.set_alignment)
        layer = platform.js.ol.layer.Image._new(
            {
                "opacity": 0.8,
            }
        )
        super().__init__(openlayers, name, layer, *args, **kwargs)
        self.opacity.ui_model_value = 0.8
        self.ui_children = [
            Row(self.visible, self.name_div, self.opacity, self.align_btn)
        ]

        self.points = []

    def set_alignment(self):
        olmap = self.openlayers.olmap
        self.points = []
        olmap.on("click", self._on_click_align)

    def _on_click_align(self, event, data):
        print('on click', event, data)
        olmap = self.openlayers.olmap
        ol = platform.js.ol
        coord = event.coordinate
        coord = ol.proj.fromLonLat(event.coordinate)
        self.points.append(np.array(coord))

        if len(self.points) < 4:
            return

        olmap.un("click", self._on_click_align)

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

        x0, y0, x1, y1 = self.layer.getSource().getImageExtent()
        x_range = []
        y_range = []
        for ex in [(x0, y0), (x0, y1), (x1, y0), (x1, y1)]:
            x, y = f(np.array(ex))
            x_range.append(x)
            y_range.append(y)

        new_extent = [min(x_range), min(y_range), max(x_range), max(y_range)]
        new_extent = [float(x) for x in new_extent]
        self.img = self.img.rotate(angle_deg, expand=True)

    def set_source(self, img, extent):
        ol = platform.js.ol
        source = ol.source.ImageStatic._new(
            {
                "url": image_to_data_uri(img),
                "projection": "EPSG:3857",
                "imageExtent": extent,
            }
        )
        self.layer.setSource(source)


class SidebarComponent(Div):
    def __init__(self, openlayers, **kwargs):
        self.openlayers = openlayers
        self.save_btn = QBtn(
            ui_icon="save",
            ui_color="primary",
        ).on_click(self.save_all)
        self.map_upload = FileUpload(
            id="file_upload",
            ui_label="Upload map file",
            ui_accept=".png,.jpg,.jpeg",
            ui_error_title="Error in Map Upload",
            ui_error_message="Please upload an Image file (png, jpg, jpeg).",
        ).on_update_model_value(self.add_layer)
        self.div_layers = Div()
        super().__init__(
            self.save_btn,
            self.div_layers,
            self.map_upload,
        )
        self.points = -1

    def save_all(self):
        # data = self._status.app.dump()
        # print(data)

        m = self.openlayers.olmap
        state = m.frameState_
        print("state", state.keys())
        center = state["viewState"]["center"]
        print("center", center)

    def build_inputs(self, layers):
        children = []

        for name in layers:
            children.append(LayerOptions(self.openlayers, name, layers[name]))

        self.div_layers.ui_children = children

    def add_layer(self):
        olmap = self.openlayers.olmap
        from webgpu.platform import js

        state = olmap.frameState_
        extent = state["extent"]
        x0, y0, x1, y1 = extent

        name = self.map_upload.filename
        data = self.map_upload.storage.get(name)
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        self.map_upload.clear_file()
        aspect = img.size[0] / img.size[1]

        y1 = y0 + (x1 - x0) / aspect

        imlayer = ImageLayer(self.openlayers, name, img)
        imlayer.set_source(img, [x0, y0, x1, y1])

        # self.im_extent = [x0, y0, x1, y1]
        # self.image_layer = layer
        # self.img = img
        #
        self.div_layers.ui_children = self.div_layers.ui_children + [
            imlayer,
        ]

        olmap.addLayer(imlayer.layer)

        # if self.points == -1:
        #     ret = olmap.on("click", self.on_click)
        #     print("onclick ret", ret)
        # self.points = []

    def on_click(self, event, data):
        return
        from webgpu.platform import js

        if self.points is None:
            return

        ol = js.ol
        coord = event.coordinate
        coord = ol["proj"]["fromLonLat"](event.coordinate)
        self.points.append(coord)

        if len(self.points) == 4:
            x0 = self.points[0][0]
            y0 = self.points[0][1]
            for i in range(4):
                self.points[i] = (
                    (self.points[i][0] - x0),
                    (self.points[i][1] - y0),
                )
            angle, f = compute_similarity_transform(self.points)
            ex0, ey0, ex1, ey1 = self.im_extent

            new_p0 = f(ex0 - x0, ey0 - y0)
            new_p1 = f(ex0 - x0, ey1 - y0)
            new_p2 = f(ex1 - x0, ey0 - y0)
            new_p3 = f(ex1 - x0, ey1 - y0)

            self.img = self.img.rotate(angle, expand=True)

            new_ex0 = min(new_p0[0], new_p1[0], new_p2[0], new_p3[0])
            new_ey0 = min(new_p0[1], new_p1[1], new_p2[1], new_p3[1])
            new_ex1 = max(new_p0[0], new_p1[0], new_p2[0], new_p3[0])
            new_ey1 = max(new_p0[1], new_p1[1], new_p2[1], new_p3[1])
            new_extent = [x0 + new_ex0, y0 + new_ey0, x0 + new_ex1, y0 + new_ey1]
            new_extent = [float(x) for x in new_extent]
            self.im_extent = new_extent

            source = ol["source"]["ImageStatic"]._new(
                {
                    "url": image_to_data_uri(self.img),
                    "projection": "EPSG:3857",
                    "imageExtent": new_extent,
                }
            )
            self.image_layer.setSource(source)
            self.points = []
