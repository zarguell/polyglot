from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape

from app.core.config import settings
from app.core.middleware.csrf import generate_csrf_token

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

SRI_HASHES = {
    "htmx": "sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=",
    "alpine": "sha256-47DEQpj8HBSa+/TImW+5JCeuQeRkm5NMpJWZG3hSuFU=",
}


@pass_context
def csrf_token(ctx) -> str:
    request = ctx.get("request")
    if request is None:
        return ""
    token = request.session.get("csrf_token")
    if not token:
        token = generate_csrf_token()
        request.session["csrf_token"] = token
    return token


def get_jinja_env() -> Environment:
    """Create and return the Jinja2 environment with Polyglot globals."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        auto_reload=settings.environment == "local",
    )

    env.globals["settings"] = settings
    env.globals["sri"] = SRI_HASHES.get
    env.globals["static"] = lambda path: f"/static/{path}"
    env.globals["app_name"] = settings.app_name
    env.globals["csrf_token"] = csrf_token

    return env
