from ngapp import AppAccessConfig, AppConfig, asset
from .app import Mapp

_DESCRIPTION = """Map App to visualizes different maps and upload/align images of plans, based on CERBSim webapp and using openlayers."""

config = AppConfig(
    name="Mapp",
    version="0.0.1",
    python_class=Mapp,
    frontend_pip_dependencies=["pillow"],
    frontend_dependencies=[],
    description=_DESCRIPTION,
    compute_environments=[],
    access=AppAccessConfig(),
    image=asset("logo.webp"),
)
