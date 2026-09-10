from dataclasses import dataclass
from typing import Literal

from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.logging import (
    get_logger,
)


logger = get_logger(__name__)


DependencyStatus = Literal[
    "ok",
    "unavailable",
    "disabled",
]


@dataclass(
    frozen=True,
    slots=True,
)
class DependencyCheck:
    """
    Result of one infrastructure
    dependency check.
    """

    status: DependencyStatus


@dataclass(
    frozen=True,
    slots=True,
)
class ReadinessResult:
    """
    Combined application readiness result.
    """

    ready: bool

    database: DependencyCheck

    redis: DependencyCheck


class HealthService:
    """
    Check infrastructure dependencies required
    for the application to serve requests.
    """

    # =========================================================
    # Database
    # =========================================================

    @staticmethod
    async def _check_database(
        session: AsyncSession,
    ) -> DependencyCheck:
        try:
            await session.execute(
                text("SELECT 1")
            )

            return DependencyCheck(
                status="ok"
            )

        except Exception as exc:
            logger.error(
                "database_readiness_check_failed",
                error_type=(
                    type(exc).__name__
                ),
            )

            return DependencyCheck(
                status="unavailable"
            )

    # =========================================================
    # Redis
    # =========================================================

    @staticmethod
    async def _check_redis(
        redis_client: Redis,
        *,
        redis_required: bool,
    ) -> DependencyCheck:

        # -----------------------------------------------------
        # Redis may be disabled when rate limiting is disabled.
        # -----------------------------------------------------

        if not redis_required:
            return DependencyCheck(
                status="disabled"
            )

        try:
            result = (
                await redis_client.ping()
            )

            if not result:
                return DependencyCheck(
                    status="unavailable"
                )

            return DependencyCheck(
                status="ok"
            )

        except Exception as exc:
            logger.error(
                "redis_readiness_check_failed",
                error_type=(
                    type(exc).__name__
                ),
            )

            return DependencyCheck(
                status="unavailable"
            )

    # =========================================================
    # Combined readiness
    # =========================================================

    async def check_readiness(
        self,
        *,
        session: AsyncSession,
        redis_client: Redis,
        redis_required: bool,
    ) -> ReadinessResult:

        database = (
            await self._check_database(
                session
            )
        )

        redis = (
            await self._check_redis(
                redis_client,
                redis_required=(
                    redis_required
                ),
            )
        )

        database_ready = (
            database.status == "ok"
        )

        redis_ready = (
            redis.status
            in {
                "ok",
                "disabled",
            }
        )

        return ReadinessResult(
            ready=(
                database_ready
                and redis_ready
            ),
            database=database,
            redis=redis,
        )