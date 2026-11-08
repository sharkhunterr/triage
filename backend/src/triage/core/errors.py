"""The error envelope: ``{"error": {"code", "message", "details"}}`` for every 4xx/5xx."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from triage.adapters.types import ServiceError


class TriageError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None, code: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        if code:
            self.code = code


class NotFound(TriageError):
    status_code = 404
    code = "not_found"


class Conflict(TriageError):
    status_code = 409
    code = "conflict"


class Unauthorized(TriageError):
    status_code = 401
    code = "unauthorized"


class Forbidden(TriageError):
    status_code = 403
    code = "forbidden"


class Gone(TriageError):
    status_code = 410
    code = "gone"


class TooManyRequests(TriageError):
    status_code = 429
    code = "too_many_requests"


def _envelope(status: int, code: str, message: str, details: dict[str, Any] | None = None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"code": code, "message": message, "details": details or {}}}
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(TriageError)
    async def _triage(_request: Request, exc: TriageError) -> JSONResponse:
        return _envelope(exc.status_code, exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [{"loc": list(e["loc"]), "msg": e["msg"]} for e in exc.errors()]
        return _envelope(422, "invalid", "Invalid request", {"errors": errors})

    @app.exception_handler(ServiceError)
    async def _service(_request: Request, exc: ServiceError) -> JSONResponse:
        return _envelope(503, "service_unavailable", exc.message, {"service": exc.service})

    @app.exception_handler(StarletteHTTPException)
    async def _http(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _envelope(exc.status_code, "http_error", str(exc.detail))
