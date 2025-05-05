from webapp_client import AppAccessConfig, AppConfig
from .app import Mapp

_DESCRIPTION = """Map App to visualizes different maps and upload/align plans/images, based on Openlayers"""

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
