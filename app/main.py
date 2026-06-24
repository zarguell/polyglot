from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.public import router as public_router
from app.api.system import router as system_router
from app.core.config import settings
from app.core.errors import AppError, app_error_handler, generic_exception_handler
from app.core.logging import setup_logging
from app.core.middleware import (
    AuditContextMiddleware,
    BodyCacheMiddleware,
    CSRFMiddleware,
    RequestIdMiddleware,
    SecurityHeadersMiddleware,
    StructuredLoggingMiddleware,
)
from app.core.security import generate_nonce

logger = structlog.get_logger()

SESSION_COOKIE_NAME = f"{settings.app_name.lower().replace(' ', '_')}_session"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup/shutdown."""
    setup_logging()
    logger.info("app_starting", environment=settings.environment, app_name=settings.app_name)

    # Discover and load components
    _load_components(app)

    yield

    logger.info("app_stopping")


def _load_components(app: FastAPI) -> None:
    """Import and register activated components."""
    import importlib
    import pkgutil

    import app.components as components_pkg

    discovered = [
        name
        for _, name, is_pkg in pkgutil.iter_modules(components_pkg.__path__)
        if is_pkg and name != "__init__"
    ]

    active = discovered
    if settings.installed_components is not None:
        active = [c for c in discovered if c in settings.installed_components]

    for name in active:
        try:
            module = importlib.import_module(f"app.components.{name}")
            if hasattr(module, "register"):
                module.register(app=app, settings=settings)
                logger.info("component_registered", name=name)
        except Exception:
            logger.exception("component_load_failed", name=name)


def create_app() -> FastAPI:
    """Factory: build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs" if settings.enable_openapi else None,
        redoc_url="/redoc" if settings.enable_openapi else None,
        lifespan=lifespan,
    )

    # ── Error handlers ──
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[type-var]
    app.add_exception_handler(Exception, generic_exception_handler)  # type: ignore[type-var]

    # ── Middleware (last added = outermost = called first inbound) ──
    app.add_middleware(RequestIdMiddleware)  # innermost
    app.add_middleware(StructuredLoggingMiddleware)

    class NonceMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request.state.nonce = generate_nonce()
            return await call_next(request)

    app.add_middleware(NonceMiddleware)  # type: ignore[arg-type]

    app.add_middleware(CSRFMiddleware)  # CSRF before Session
    app.add_middleware(AuditContextMiddleware)  # type: ignore[arg-type]  # audit after Session
    app.add_middleware(  # Session wraps outside CSRF
        SessionMiddleware,  # → request.session available in CSRF
        secret_key=settings.secret_key.get_secret_value(),
        session_cookie=SESSION_COOKIE_NAME,
        max_age=settings.session_max_age_seconds,
        same_site="lax",
        https_only=settings.environment != "local",
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(BodyCacheMiddleware)  # outermost — cache body before any BaseHTTPMiddleware

    # ── Static files ──
    from pathlib import Path

    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # ── Routes ──
    app.include_router(public_router, prefix="")
    app.include_router(auth_router, prefix="")
    app.include_router(system_router, prefix="")
    app.include_router(admin_router, prefix="")

    return app


app = create_app()
