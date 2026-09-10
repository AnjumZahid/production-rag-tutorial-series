from dataclasses import dataclass
from hashlib import sha256
from time import time

from redis.asyncio import Redis
from redis.exceptions import RedisError

from backend.app.core.config import (
    settings,
)
from backend.app.core.logging import (
    get_logger,
)
from backend.app.rate_limiting.exceptions import (
    RateLimitBackendError,
)


logger = get_logger(__name__)


# =============================================================
# Atomic Redis Lua script
# =============================================================

_RATE_LIMIT_SCRIPT = """
local current = redis.call("INCR", KEYS[1])

if current == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end

local ttl = redis.call("TTL", KEYS[1])

if ttl < 0 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
    ttl = tonumber(ARGV[1])
end

return {current, ttl}
""".strip()


# =============================================================
# Rate-limit decision
# =============================================================


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """
    Result returned by one rate-limit check.
    """

    allowed: bool
    limit: int
    remaining: int
    retry_after: int
    reset_after: int
    current: int
    backend_available: bool = True


# =============================================================
# Redis rate limiter
# =============================================================


class RedisRateLimiter:
    """
    Redis-backed atomic fixed-window rate limiter.
    """

    def __init__(
        self,
        *,
        client: Redis,
        key_prefix: str,
        enabled: bool,
        fail_open: bool,
    ) -> None:
        self.client = client

        self.key_prefix = (
            key_prefix
        )

        self.enabled = enabled
        self.fail_open = fail_open

    # ---------------------------------------------------------
    # Redis connectivity
    # ---------------------------------------------------------

    async def ping(self) -> bool:
        """
        Confirm Redis connectivity.
        """

        result = await self.client.ping()

        return bool(result)

    # ---------------------------------------------------------
    # Privacy-safe identifier hashing
    # ---------------------------------------------------------

    @staticmethod
    def _identifier_hash(
        identifier: str,
    ) -> str:
        """
        Hash IP/user identifiers before storing them
        inside Redis key names.
        """

        return sha256(
            identifier.encode(
                "utf-8"
            )
        ).hexdigest()

    # ---------------------------------------------------------
    # Redis key
    # ---------------------------------------------------------

    def build_key(
        self,
        *,
        scope: str,
        identifier: str,
        window_seconds: int,
        timestamp: int | None = None,
    ) -> str:
        """
        Build one fixed-window Redis key.

        Format:

        prefix:scope:identifier_hash:bucket
        """

        effective_timestamp = (
            timestamp
            if timestamp is not None
            else int(time())
        )

        bucket = (
            effective_timestamp
            // window_seconds
        )

        identifier_hash = (
            self._identifier_hash(
                identifier
            )
        )

        return (
            f"{self.key_prefix}:"
            f"{scope}:"
            f"{identifier_hash}:"
            f"{bucket}"
        )

    # ---------------------------------------------------------
    # Rate-limit check
    # ---------------------------------------------------------

    async def check(
        self,
        *,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitDecision:
        """
        Increment and evaluate one fixed-window bucket.
        """

        if limit < 1:
            raise ValueError(
                "limit must be at least 1."
            )

        if window_seconds < 1:
            raise ValueError(
                "window_seconds must be "
                "at least 1."
            )

        # -----------------------------------------------------
        # Feature disabled
        # -----------------------------------------------------

        if not self.enabled:
            return RateLimitDecision(
                allowed=True,
                limit=limit,
                remaining=limit,
                retry_after=0,
                reset_after=(
                    window_seconds
                ),
                current=0,
            )

        current_timestamp = int(
            time()
        )

        # -----------------------------------------------------
        # Calculate the end of the current fixed window
        # -----------------------------------------------------

        bucket_end = (
            (
                current_timestamp
                // window_seconds
            )
            + 1
        ) * window_seconds

        seconds_until_reset = max(
            bucket_end
            - current_timestamp,
            1,
        )

        key = self.build_key(
            scope=scope,
            identifier=identifier,
            window_seconds=(
                window_seconds
            ),
            timestamp=(
                current_timestamp
            ),
        )

        # -----------------------------------------------------
        # Atomic Redis operation
        # -----------------------------------------------------

        try:
            result = await self.client.eval(
                _RATE_LIMIT_SCRIPT,
                1,
                key,
                seconds_until_reset,
            )

            current = int(
                result[0]
            )

            ttl = max(
                int(result[1]),
                1,
            )

        # -----------------------------------------------------
        # Redis unavailable
        # -----------------------------------------------------

        except RedisError as exc:
            logger.error(
                "rate_limit_backend_failed",
                scope=scope,
                error_type=(
                    type(exc).__name__
                ),
                fail_open=(
                    self.fail_open
                ),
            )

            # -------------------------------------------------
            # Fail-open mode
            # -------------------------------------------------

            if self.fail_open:
                return RateLimitDecision(
                    allowed=True,
                    limit=limit,
                    remaining=limit,
                    retry_after=0,
                    reset_after=(
                        window_seconds
                    ),
                    current=0,
                    backend_available=False,
                )

            # -------------------------------------------------
            # Fail-closed mode
            # -------------------------------------------------

            raise RateLimitBackendError(
                details={
                    "scope": scope,
                    "error_type": (
                        type(exc).__name__
                    ),
                }
            ) from None

        # -----------------------------------------------------
        # Decision
        # -----------------------------------------------------

        remaining = max(
            limit - current,
            0,
        )

        allowed = (
            current <= limit
        )

        retry_after = (
            0
            if allowed
            else ttl
        )

        return RateLimitDecision(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            retry_after=retry_after,
            reset_after=ttl,
            current=current,
        )

    # ---------------------------------------------------------
    # Test cleanup helper
    # ---------------------------------------------------------

    async def clear_current_bucket(
        self,
        *,
        scope: str,
        identifier: str,
        window_seconds: int,
    ) -> None:
        """
        Delete the current Redis bucket.

        Primarily used by tests.
        """

        key = self.build_key(
            scope=scope,
            identifier=identifier,
            window_seconds=(
                window_seconds
            ),
        )

        await self.client.delete(
            key
        )


# =============================================================
# Shared Redis client / limiter
# =============================================================

_redis_client: Redis | None = None

_rate_limiter: (
    RedisRateLimiter | None
) = None


def get_redis_client() -> Redis:
    """
    Return one process-wide async Redis client.
    """

    global _redis_client

    if _redis_client is None:
        _redis_client = (
            Redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=(
                    settings
                    .redis_socket_connect_timeout_seconds
                ),
                socket_timeout=(
                    settings
                    .redis_socket_timeout_seconds
                ),
                health_check_interval=30,
            )
        )

    return _redis_client


def get_rate_limiter() -> RedisRateLimiter:
    """
    Return the shared process-wide rate limiter.
    """

    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = (
            RedisRateLimiter(
                client=(
                    get_redis_client()
                ),
                key_prefix=(
                    settings
                    .rate_limit_key_prefix
                ),
                enabled=(
                    settings
                    .rate_limit_enabled
                ),
                fail_open=(
                    settings
                    .rate_limit_fail_open
                ),
            )
        )

    return _rate_limiter


async def close_rate_limiter() -> None:
    """
    Close Redis connections during application shutdown.
    """

    global _redis_client
    global _rate_limiter

    if _redis_client is not None:
        await _redis_client.aclose()

    _redis_client = None
    _rate_limiter = None