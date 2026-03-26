import logging
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("miro.error")


class AppError(Exception):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(message)


def build_error_payload(
    *,
    request_id: str | None,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
        "requestId": request_id,
    }


def raise_feature_not_ready(module_name: str) -> None:
    raise AppError(
        status_code=501,
        code="feature_not_ready",
        message=f"{module_name} module is scaffolded but not implemented in phase 1.",
        details={"module": module_name, "phase": "backend_foundation"},
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content=build_error_payload(
            request_id=request_id,
            code="validation_error",
            message="Request validation failed.",
            details={"errors": exc.errors()},
        ),
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content=build_error_payload(
            request_id=request_id,
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logger.exception(
        "Unhandled application exception",
        extra={"request_id": request_id, "path": request.url.path},
    )
    return JSONResponse(
        status_code=500,
        content=build_error_payload(
            request_id=request_id,
            code="internal_server_error",
            message="An unexpected error occurred.",
        ),
    )
