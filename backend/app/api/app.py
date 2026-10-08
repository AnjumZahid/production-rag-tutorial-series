# uv add fastapi "uvicorn[standard]" python-multipart httpx

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.dependencies import close_shared_resources
from backend.app.api.routes import router
from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.database.session import close_database_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield

    await close_shared_resources()
    await close_database_connection()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.exception_handler(AppError)
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                }
            },
        )

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

    return app