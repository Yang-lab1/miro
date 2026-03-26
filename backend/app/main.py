from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.errors import (
    AppError,
    app_error_handler,
    request_validation_error_handler,
    unhandled_exception_handler,
)
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def create_application() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    docs_url = "/docs" if settings.enable_docs else None
    redoc_url = "/redoc" if settings.enable_docs else None

    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.resolved_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, request_validation_error_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    app.include_router(api_router, prefix=settings.api_prefix)

    return app


app = create_application()
