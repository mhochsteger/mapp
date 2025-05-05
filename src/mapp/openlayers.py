from webapp_client.basecomponent import Event
from webapp_client.components import Div, Event


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

        # self.on("map_loaded", self._on_map_loaded)

    def _on_mounted(self):
        from webgpu.platform import js
        print("JS", js)

        if js.ol is None:
            print("ol is none, import package")
            js.importPackage("https://cdn.jsdelivr.net/npm/ol@v10.5.0/dist/ol.js")
            print("add style")
            js.addStyleFile("https://cdn.jsdelivr.net/npm/ol@v10.5.0/ol.css")
            print("import olms")
            js.importPackage(
                "https://cdn.jsdelivr.net/npm/ol-mapbox-style@v12.6.0/dist/olms.js"
            )
            print("done")

        ol = js.ol
        ol["proj"]["useGeographic"]()
        osm = ol["source"]["OSM"]._new()

        view = ol["View"]._new(
            {
                "center": [15.1, 48.15],
                "zoom": 17,
            }
        )
        self.layers["osm"] = ol["layer"]["Tile"]._new(
            {
                "source": osm,
            }
        )
        fill = ol["style"]["Fill"]._new(
            {
                "color": "rgba(255, 255, 255, 0.1)",
            }
        )
        stroke = ol["style"]["Stroke"]._new(
            {
                "color": "#3309CC",
                "width": 1.25,
            }
        )

        ol_style = ol["style"]["Style"]._new(
            {
                "image": ol["style"]["Circle"]._new(
                    {
                        "fill": fill,
                        "stroke": stroke,
                        "radius": 5,
                    }
                ),
                "fill": fill,
                "stroke": stroke,
                "text": ol["style"]["Text"]._new(
                    {
                        "fill": fill,
                        "stroke": stroke,
                    }
                ),
            }
        )

        # self.layers["mapbox"] = ol["layer"]["Vector"]._new(
        #     {
        #         "styleUrl": "https://kataster.bev.gv.at/styles/style_basic.json",
        #     }
        # )
        kataster_src = ol["source"]["VectorTile"]._new(
            {
                "url": "https://kataster.bev.gv.at/tiles/kataster/{z}/{x}/{y}.pbf",
                "format": ol["format"]["MVT"]._new(),
                "maxZoom": 16,
                "style": ol_style,
            }
        )
        kataster = ol["layer"]["VectorTile"]._new(
            {
                "declutter": True,
                "source": kataster_src,
                "style": ol_style,
                # "styleUrl": "https://kataster.bev.gv.at/styles/style_basic.json",
            }
        )

        symbole_src = ol["source"]["VectorTile"]._new(
            {
                "url": "https://kataster.bev.gv.at/tiles/symbole/{z}/{x}/{y}.pbf",
                "format": ol["format"]["MVT"]._new(),
                "maxZoom": 16,
            }
        )

        # style_url = "https://kataster.bev.gv.at/styles/kataster/style_basic.json"
        # style_url = style_url.replace("style_basic", "style_vermv")

        kataster_style = "vermv"  # basic, gis, vermv, ortho
        symbole_style = "gis"  # basic, gis, vermv, ortho

        symbole = ol["layer"]["VectorTile"]._new(
            {
                "declutter": True,
                "source": symbole_src,
                "style": ol_style,
            }
        )
        js.console['log']("symbole", symbole)
        js.console['log']("kataster", kataster)
        js.olms["applyStyle"](
            symbole,
            f"https://kataster.bev.gv.at/styles/symbole/style_{symbole_style}.json",
        )
        js.olms["applyStyle"](
            kataster,
            f"https://kataster.bev.gv.at/styles/kataster/style_{kataster_style}.json",
        )
        self.layers["kataster"] = kataster
        self.layers["symbole"] = symbole
        self.olmap = ol["Map"]._new(
            {
                "layers": [self.layers["osm"], kataster, symbole],
                "target": "map",
                "view": view,
            }
        )
        js.console['log']("olmap", self.olmap)
        self.sidebar.build_inputs(self.layers)



