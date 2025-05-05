from webapp_client import AppAccessConfig, AppConfig
from .app import Mapp

_DESCRIPTION = """Map App to visualizes different maps and upload plans/images, based on Leaflet"""

config = AppConfig(
    name="Mapp",
    version="0.0.1",
    python_class=Mapp,
    frontend_pip_dependencies=['pillow'],
    frontend_dependencies=[],
    description=_DESCRIPTION,
    compute_environments=[],
    access=AppAccessConfig(),
)
