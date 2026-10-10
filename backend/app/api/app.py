from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.app.api.auth_routes import router as auth_router
from backend.app.api.dependencies import close_shared_resources
from backend.app.api.routes import router as rag_router
from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.database.session import close_database_connection


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None, None]:
    yield

    await close_shared_resources()
    await close_database_connection()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(auth_router)
    app.include_router(rag_router)

    register_exception_handlers(app)

    return app


def register_exception_handlers(
    app: FastAPI,
) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        headers = None

        if exc.status_code == 401:
            headers = {
                "WWW-Authenticate": "Bearer",
            }

        return JSONResponse(
            status_code=exc.status_code,
            headers=headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                    "details": {},
                }
            },
        )