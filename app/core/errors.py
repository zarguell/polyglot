from __future__ import annotations

import structlog
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse
from structlog.contextvars import bind_contextvars, clear_contextvars

logger = structlog.get_logger()


class AppError(Exception):
    """Base application error with safe user-facing message."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        log_message: str | None = None,
    ) -> None:
        self.message = message
        self.status_code = status_code
        self.log_message = log_message or message


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message=message, status_code=404)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden") -> None:
        super().__init__(message=message, status_code=403)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message=message, status_code=401)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse | HTMLResponse:
    bind_contextvars(path=str(request.url), method=request.method)
    logger.error("app_error", error=exc.log_message, status_code=exc.status_code)
    clear_contextvars()

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        return HTMLResponse(
            content=f"<h1>{exc.status_code}</h1><p>{exc.message}</p>",
            status_code=exc.status_code,
            media_type="text/html",
        )
    return JSONResponse(
        content={"detail": exc.message, "status_code": exc.status_code},
        status_code=exc.status_code,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse | HTMLResponse:
    bind_contextvars(path=str(request.url), method=request.method)
    logger.exception("unhandled_exception", error=str(exc))
    clear_contextvars()
    return await app_error_handler(request, AppError())
