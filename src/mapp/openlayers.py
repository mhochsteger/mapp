import base64
from typing import Literal

from ngapp.components import Div
from webgpu import platform


def get_kataster_layer(style: Literal["basic", "gis", "vermv", "ortho"] = "ortho"):
    ol = platform.js.ol
    kataster = ol.layer.VectorTile._new(
        {
            "declutter": True,
            "source": ol.source.VectorTile._new(
                {
                    "url": "https://kataster.bev.gv.at/tiles/kataster/{z}/{x}/{y}.pbf",
                    "format": ol.format.MVT._new(),
                    "maxZoom": 16,
                }
            ),
        }
    )
    platform.js.olms["applyStyle"](
        kataster,
        f"https://kataster.bev.gv.at/styles/kataster/style_{style}.json",
    )
    return kataster


def get_symbole_layer(style: Literal["basic", "gis", "vermv", "ortho"] = "gis"):
    ol = platform.js.ol
    symbole = ol.layer.VectorTile._new(
        {
            "declutter": True,
            "source": ol.source.VectorTile._new(
                {
                    "url": "https://kataster.bev.gv.at/tiles/symbole/{z}/{x}/{y}.pbf",
                    "format": ol.format.MVT._new(),
                    "maxZoom": 16,
                }
            ),
        }
    )
    platform.js.olms["applyStyle"](
        symbole,
        f"https://kataster.bev.gv.at/styles/symbole/style_{style}.json",
    )
    return symbole


class OpenLayersComponent(Div):
    def __init__(self, **kwargs):
        super().__init__(
            **kwargs,
            ui_style={"width": "75vw", "height": "100vh"},
            ui_class="map",
        )
        self._props["id"] = "map"
        self.on_mounted(self._on_mounted)
        self.layers = {}
        self.wms = None
        self.protobuf = None
        self.on_before_save(self._on_before_save)
        self.on_load(self._on_load)
        self.olmap = None

        self.ol = None

    def _on_before_save(self):
        view = self.olmap.getView()
        center = view.getCenter()
        zoom = view.getZoom()
        self.storage.set("view", {"center": center, "zoom": zoom})

    def _on_load(self):
        view_data = self.storage.get("view")
        if view_data:
            view = self.olmap.getView()
            view.setCenter(view_data["center"])
            view.setZoom(view_data["zoom"])

    def _on_mounted(self):
        if platform.js.ol is None:
            platform.js.importPackage(
                "https://cdn.jsdelivr.net/npm/ol@v10.5.0/dist/ol.js"
            )
            platform.js.addStyleFile("https://cdn.jsdelivr.net/npm/ol@v10.5.0/ol.css")
            platform.js.importPackage(
                "https://cdn.jsdelivr.net/npm/ol-mapbox-style@v12.6.0/dist/olms.js"
            )

        ol = self.ol = platform.js.ol
        ol.proj.useGeographic()

        cap_url = "https://mapsneu.wien.gv.at/basemapneu/1.0.0/WMTSCapabilities.xml"

        import pyodide.http

        text = pyodide.http.open_url(cap_url).read()
        parser = ol.format.WMTSCapabilities._new()
        result = parser.read(text)

        options = ol.source.WMTS.optionsFromCapabilities(
            result,
            {"layer": "bmaporthofoto30cm", "crossOrigin": "anonymous"},
        )
        options.tileGrid.maxZoom = 18

        ortho = ol.layer.Tile._new(
            {"opacity": 1, "source": ol.source.WMTS._new(options), "maxResolution": 18}
        )

        # example url https://tiles.arcanum.com/mercator/cadastral/16/35738/22729?v=54
        #  -H 'Referer: https://maps.arcanum.com/'   \
        import json

        options = {
            "method": "GET",
            "headers": {
                # "Origin": "https://maps.arcanum.com",
                "x-corsfix-headers": json.dumps(
                    {
                        # "Origin": "https://maps.arcanum.com",
                        "Referer": "https://maps.arcanum.com",
                    }
                ),
            },
        }

        async def load_tile(imageTile, src):
            storage = platform.js.localStorage
            key = "get_url_" + src
            data = storage["get_url_" + src]
            if data is None:
                from pyodide.http import pyfetch

                url = "https://proxy.corsfix.com/?url=" + src
                headers = options["headers"]
                try:
                    response = await pyfetch(url, headers=headers)
                    if response.ok:
                        data_type = response.headers.get("content-type").replace(
                            "image/", ""
                        )
                        data = f"data:{data_type};base64,{base64.b64encode(await response.bytes()).decode()}"
                        storage[key] = data
                except Exception as e:
                    print(f"Error loading tile: {e}")
            if data is not None:
                imageTile.getImage().src = data

        arcanum_src = ol.source.XYZ._new(
            {
                "url": "https://tiles.arcanum.com/mercator/cadastral/{z}/{x}/{y}",
                "tileLoadFunction": load_tile,
                "maxZoom": 18,
            }
        )

        arcanum = ol.layer.Tile._new(
            {
                "source": arcanum_src,
                "opacity": 1,
            }
        )

        arcanum.setVisible(False)

        platform.js.console.log("src", arcanum_src)
        platform.js.console.log("arc", arcanum)
        view_data = self.storage.get("view")
        if not view_data:
            view_data = {"center": [15.1, 48.15], "zoom": 17}
        view = ol.View._new(view_data)

        osm = ol.layer.Tile._new({"source": ol.source.OSM._new()})

        kataster = get_kataster_layer()
        symbole = get_symbole_layer()

        self.layers["Osm"] = osm
        self.layers["Ortho"] = ortho
        self.layers["Kataster"] = kataster
        self.layers["Symbole"] = symbole
        self.layers["Arcanum"] = arcanum
        self.olmap = ol["Map"]._new(
            {
                "layers": [osm, ortho, kataster, symbole, arcanum],
                "target": "map",
                "view": view,
            }
        )
        self.sidebar.build_inputs(self.layers)
