from __future__ import annotations

from pathlib import Path

from jinja2 import ChoiceLoader, Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.core.templates import SRI_HASHES, TEMPLATES_DIR, csrf_token

_COMPONENT_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def get_component_env() -> Environment:
    """Create a Jinja2 environment that falls back to the main app templates.

    This allows component templates to extend base.html and include
    shared partials while keeping their own templates self-contained.
    """
    env = Environment(
        loader=ChoiceLoader(
            [
                FileSystemLoader(str(_COMPONENT_TEMPLATES_DIR)),
                FileSystemLoader(str(TEMPLATES_DIR)),
            ]
        ),
        autoescape=select_autoescape(["html", "xml"]),
        auto_reload=settings.environment == "local",
    )

    env.globals["settings"] = settings
    env.globals["sri"] = SRI_HASHES.get
    env.globals["static"] = lambda path: f"/static/{path}"
    env.globals["app_name"] = settings.app_name
    env.globals["csrf_token"] = csrf_token

    return env
