from webapp_client.components import Row
from webapp_client.app import App

from .openlayers import OpenLayersComponent
from .sidebar import SidebarComponent

class Mapp(App):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layers = OpenLayersComponent(id="leaflet")
        sidebar = SidebarComponent(layers, id="sidebar")
        layers.sidebar = sidebar
        self.component = Row(layers, sidebar)

