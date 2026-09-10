from fastapi import (
    APIRouter,
    Depends,
    Response,
    status,
)
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.api.dependencies import (
    get_database_session_dependency,
)
from backend.app.api.health_schemas import (
    DependencyHealthResponse,
    LivenessResponse,
    ReadinessChecksResponse,
    ReadinessResponse,
)
from backend.app.core.config import (
    settings,
)
from backend.app.rate_limiting.service import (
    get_redis_client,
)
from backend.app.services.health_service import (
    HealthService,
)


router = APIRouter(
    prefix="/health",
    tags=["System"],
)


# =============================================================
# Liveness
# =============================================================


@router.get(
    "/live",
    response_model=(
        LivenessResponse
    ),
)
async def liveness_check(
) -> LivenessResponse:
    """
    Confirm that the FastAPI process is running.

    This endpoint deliberately does not check
    MySQL, Redis, Chroma, embeddings, or the LLM.
    """

    return LivenessResponse(
        status="alive",
        application=(
            settings.app_name
        ),
        environment=(
            settings.app_environment
        ),
    )


# =============================================================
# Readiness
# =============================================================


@router.get(
    "/ready",
    response_model=(
        ReadinessResponse
    ),
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": (
                ReadinessResponse
            ),
            "description": (
                "One or more required "
                "dependencies are unavailable."
            ),
        },
    },
)
async def readiness_check(
    response: Response,
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
    redis_client: Redis = Depends(
        get_redis_client
    ),
) -> ReadinessResponse:
    """
    Confirm that infrastructure required
    by the application is available.
    """

    result = (
        await HealthService()
        .check_readiness(
            session=session,
            redis_client=redis_client,
            redis_required=(
                settings
                .rate_limit_enabled
            ),
        )
    )

    # ---------------------------------------------------------
    # Health route still returns a structured response body,
    # but changes HTTP status to 503 when not ready.
    # ---------------------------------------------------------

    if not result.ready:
        response.status_code = (
            status
            .HTTP_503_SERVICE_UNAVAILABLE
        )

    return ReadinessResponse(
        status=(
            "ready"
            if result.ready
            else "not_ready"
        ),
        checks=(
            ReadinessChecksResponse(
                database=(
                    DependencyHealthResponse(
                        status=(
                            result
                            .database
                            .status
                        )
                    )
                ),
                redis=(
                    DependencyHealthResponse(
                        status=(
                            result
                            .redis
                            .status
                        )
                    )
                ),
            )
        ),
    )