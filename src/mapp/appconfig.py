import os
from webapp_client import AppAccessConfig, AppConfig, utils
from .app import Mapp

_DESCRIPTION = """Map App to visualizes different maps and upload/align images of plans, based on CERBSim webapp and using openlayers."""


def load_image(filename):
    picture = os.path.join(os.path.dirname(__file__), filename)
    return utils.load_image(picture)


config = AppConfig(
    name="Mapp",
    version="0.0.1",
    python_class=Mapp,
    frontend_pip_dependencies=["pillow"],
    frontend_dependencies=[],
    description=_DESCRIPTION,
    compute_environments=[],
    access=AppAccessConfig(),
    image=load_image("logo.webp"),
)
