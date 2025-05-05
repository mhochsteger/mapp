from webapp_client.basecomponent import Component, Event



class LeafletComponent(Component):
    def __init__(self, *args, **kwargs):
        super().__init__(
            "LeafletComponent",
            *args,
            **kwargs,
            ui_style={"width": "80vw", "height": "80vh"}
        )
        self._props["id"] = "leaflet"
        self.on_mounted(self._on_mounted)
        self.layers = {}
        self.wms = None
        self.protobuf = None

        self.on("map_loaded", self._on_map_loaded)

    def _on_mounted(self):
        from webgpu.platform import js
        js.importPackage('https://cdn.jsdelivr.net/npm/lil-gui@0.20')

    def _on_map_loaded(self, event: Event):
        self.map = event.value["map"]
        self.L = event.value["L"]
        self.protobuf = event.value["protobuf"]
        self.wms = event.value["wms"]
        self.map._call_method("setView", [[48.12, 15.04], 13])
        self.add_tile_layer("OpenStreetMap", *_OSM_LAYER)
        self.add_wms_tile_layer("Orthophoto", *_ORTHO_LAYER)
        # self.add_wms_tile_layer("Hora", *_HORA_LAYER)
        self.add_vectorgrid_protobuf_layer("Grundstücke", *_GRUNDSTUECK_LAYER)

        # def set_wms(wms):
        #     print("HAVE WMS", wms)
        #     self.wms = wms
        #     # self.add_wms_tile_layer("Orthophoto", *_ORTHO_LAYER)
        #     # self.add_wms_tile_layer("Hora", *_HORA_LAYER)
        #
        # self.L["tileLayer"]._call_method(
        #     "valueOf", ["wms"], _result_callback=set_wms
        # )
        #
        # def set_protobuf(protobuf):
        #     print("HAVE WMS", protobuf)
        #     self.protobuf = protobuf
        #     self.add_vectorgrid_protobuf_layer("Grundstcke", *_GRUNDSTUECK_LAYER)
        #
        # self.L["vectorGrid"]._call_method(
        #     "valueOf", ["protobuf"], _result_callback=set_protobuf
        # )

        print("map", self.map)
        print("L", self.L)

    def add_tile_layer(self, name, url, options):
        def callback(layer):
            layer._call_method("addTo", [self.map])
            self.layers[name] = layer
            self._handle("layer_added", {"name": name, "layer": layer})

        self.L["tileLayer"](url, options, _result_callback=callback)

    def add_wms_tile_layer(self, name, url, options):
        def callback(layer):
            layer._call_method("addTo", [self.map])
            self.layers[name] = layer
            self._handle("layer_added", {"name": name, "layer": layer})

        self.wms(url, options, _result_callback=callback)

    def add_vectorgrid_protobuf_layer(self, name, url, options):
        def callback(layer):
            layer._call_method("addTo", [self.map])
            self.layers[name] = layer
            self._handle("layer_added", {"name": name, "layer": layer})

        self.protobuf(url, options, _result_callback=callback)


MAX_ZOOM = 25

_OSM_LAYER = (
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        "maxZoom": MAX_ZOOM,
    },
)

_ORTHO_LAYER = (
    "https://kataster.bev.gv.at/ortho/ows",
    {
        "format": "image/jpeg",
        "transparent": True,
        "layers": "inspire:AT_BEV_OI",
        "tileSize": 512,
        "maxNativeZoom": 18,
        "maxZoom": MAX_ZOOM,
        "version": "1.3.0",
    },
)

_HORA_LAYER = (
    "https://tiles.lfrz.gv.at/hora",
    {
        "format": "image/png",
        "transparent": True,
        "layers": "hwrz",
        "tileSize": 512,
        "maxNativeZoom": 18,
        "maxZoom": MAX_ZOOM,
    },
)

_style = {
    "weight": 0.3,
    "color": "#000000",
    "interactive": False,
}

_icon = {
    "icon": {
        "options": {
            "iconUrl": "https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-violet.png",
            "iconSize": [20, 20],
            "iconAnchor": [10, 10],
        }
    }
}


def getFeatureId(*args):
    print("get feature id", args)
    return "kg"


_GRUNDSTUECK_LAYER = (
    "https://kataster.bev.gv.at/tiles/kataster/{z}/{x}/{y}.pbf",
    {
        "vectorTileLayerStyles": {
            "gnr": _icon,
            "gst": _style,
            "gst": _style
            | {
                "weight": 0.2,
                "color": "#0000FF",
                "interactive": True,
                "fill": True,
                "fillOpacity": 0.01,
            },
            "kg": _style,
            "kgp": _style,
            "ms": _style,
            "nfl": _style,
            "pg": _style,
            "pgp": _style,
        },
        "maxNativeZoom": 16,
        "maxZoom": MAX_ZOOM,
        "minZoom": 16,
        "interactive": True,
        # "getFeatureId": getFeatureId,
    },
)
