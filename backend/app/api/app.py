from collections.abc import (
    AsyncGenerator,
)
from contextlib import (
    asynccontextmanager,
)

from fastapi import (
    FastAPI,
    Request,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.middleware.httpsredirect import (
    HTTPSRedirectMiddleware,
)
from fastapi.responses import (
    JSONResponse,
)
from starlette.middleware.trustedhost import (
    TrustedHostMiddleware,
)

from backend.app.api.auth_routes import (
    router as auth_router,
)
from backend.app.api.dependencies import (
    close_shared_resources,
)
from backend.app.api.document_management_routes import (
    router as document_management_router,
)
from backend.app.api.health_routes import (
    router as health_router,
)
from backend.app.api.middleware import (
    RequestSecurityMiddleware,
)
from backend.app.api.organization_routes import (
    router as organization_router,
)
from backend.app.api.rate_limit_middleware import (
    RedisRateLimitMiddleware,
)
from backend.app.api.routes import (
    router as rag_router,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    AppError,
)
from backend.app.database.session import (
    close_database_connection,
)
from backend.app.rate_limiting.exceptions import (
    RateLimitExceededError,
)
from backend.app.rate_limiting.service import (
    close_rate_limiter,
)


# =============================================================
# Application lifespan
# =============================================================


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[
    None,
    None,
]:
    try:
        yield

    finally:
        await close_shared_resources()

        await close_rate_limiter()

        await close_database_connection()


# =============================================================
# Application factory
# =============================================================


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # =========================================================
    # Global Redis rate limiter
    #
    # Step 36A:
    # Health probes are excluded so deployment checks do not
    # consume the normal general API request quota.
    # =========================================================

    app.add_middleware(
        RedisRateLimitMiddleware,
        limit=(
            settings
            .rate_limit_general_requests
        ),
        window_seconds=(
            settings
            .rate_limit_general_window_seconds
        ),
        excluded_paths={
            "/docs",
            "/redoc",
            "/openapi.json",

            # Existing health endpoint
            "/api/v1/health",

            # Step 36A
            "/api/v1/health/live",
            "/api/v1/health/ready",
        },
    )

    # =========================================================
    # Request security middleware
    # =========================================================

    app.add_middleware(
        RequestSecurityMiddleware,
        enable_hsts=(
            settings
            .security_enable_hsts
        ),
        hsts_max_age_seconds=(
            settings
            .security_hsts_max_age_seconds
        ),
    )

    # =========================================================
    # Optional HTTPS redirect
    # =========================================================

    if settings.security_force_https:
        app.add_middleware(
            HTTPSRedirectMiddleware
        )

    # =========================================================
    # Trusted Host
    # =========================================================

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=(
            settings.trusted_hosts
        ),
    )

    # =========================================================
    # CORS
    # =========================================================

    app.add_middleware(
        CORSMiddleware,
        allow_origins=(
            settings
            .cors_allowed_origins
        ),
        allow_credentials=(
            settings
            .cors_allow_credentials
        ),
        allow_methods=[
            "GET",
            "POST",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Accept",
            "Authorization",
            "Content-Type",
            "X-Request-ID",
        ],
        expose_headers=[
            # Security
            "X-Request-ID",
            "X-Process-Time-Ms",

            # Endpoint rate limit
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",

            # Global rate limit
            "X-RateLimit-Global-Limit",
            "X-RateLimit-Global-Remaining",
            "X-RateLimit-Global-Reset",

            "Retry-After",
        ],
        max_age=600,
    )

    # =========================================================
    # Routers
    # =========================================================

    app.include_router(
        auth_router
    )

    app.include_router(
        organization_router
    )

    app.include_router(
        document_management_router,
        prefix=settings.api_prefix,
    )

    app.include_router(
        rag_router
    )

    # ---------------------------------------------------------
    # Step 36A
    # ---------------------------------------------------------

    app.include_router(
        health_router,
        prefix=settings.api_prefix,
    )

    # =========================================================
    # Exception handlers
    # =========================================================

    register_exception_handlers(
        app
    )

    return app


# =============================================================
# Exception handlers
# =============================================================


def register_exception_handlers(
    app: FastAPI,
) -> None:

    # ---------------------------------------------------------
    # Rate-limit 429
    # ---------------------------------------------------------

    @app.exception_handler(
        RateLimitExceededError
    )
    async def rate_limit_exceeded_handler(
        request: Request,
        exc: RateLimitExceededError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=(
                exc.status_code
            ),
            headers=(
                exc.headers
            ),
            content={
                "error": {
                    "code": exc.code,
                    "message": (
                        exc.message
                    ),
                    "details": (
                        exc.details
                    ),
                }
            },
        )

    # ---------------------------------------------------------
    # Controlled application errors
    # ---------------------------------------------------------

    @app.exception_handler(
        AppError
    )
    async def app_error_handler(
        request: Request,
        exc: AppError,
    ) -> JSONResponse:
        headers = None

        if exc.status_code == 401:
            headers = {
                "WWW-Authenticate": (
                    "Bearer"
                ),
            }

        return JSONResponse(
            status_code=(
                exc.status_code
            ),
            headers=headers,
            content={
                "error": {
                    "code": exc.code,
                    "message": (
                        exc.message
                    ),
                    "details": (
                        exc.details
                    ),
                }
            },
        )

    # ---------------------------------------------------------
    # Unexpected errors
    # ---------------------------------------------------------

    @app.exception_handler(
        Exception
    )
    async def unexpected_error_handler(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": (
                        "INTERNAL_SERVER_ERROR"
                    ),
                    "message": (
                        "An unexpected "
                        "error occurred."
                    ),
                    "details": {},
                }
            },
        )