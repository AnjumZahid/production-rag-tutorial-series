import asyncio
from uuid import uuid4

from redis.asyncio import Redis

from backend.app.core.config import (
    settings,
)
from backend.app.rate_limiting.service import (
    RedisRateLimiter,
)


async def main() -> None:
    client = Redis.from_url(
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
    )

    identifier = (
        f"rate-test-user-"
        f"{uuid4().hex}"
    )

    scope = (
        f"rate-test-"
        f"{uuid4().hex}"
    )

    window_seconds = 120
    limit = 3

    limiter = RedisRateLimiter(
        client=client,
        key_prefix="rag-api-test",
        enabled=True,
        fail_open=False,
    )

    try:
        # -----------------------------------------------------
        # Redis connectivity
        # -----------------------------------------------------

        assert (
            await limiter.ping()
            is True
        )

        # -----------------------------------------------------
        # Request 1
        # -----------------------------------------------------

        first = await limiter.check(
            scope=scope,
            identifier=identifier,
            limit=limit,
            window_seconds=(
                window_seconds
            ),
        )

        # -----------------------------------------------------
        # Request 2
        # -----------------------------------------------------

        second = await limiter.check(
            scope=scope,
            identifier=identifier,
            limit=limit,
            window_seconds=(
                window_seconds
            ),
        )

        # -----------------------------------------------------
        # Request 3
        # -----------------------------------------------------

        third = await limiter.check(
            scope=scope,
            identifier=identifier,
            limit=limit,
            window_seconds=(
                window_seconds
            ),
        )

        # -----------------------------------------------------
        # Request 4 — must be blocked
        # -----------------------------------------------------

        fourth = await limiter.check(
            scope=scope,
            identifier=identifier,
            limit=limit,
            window_seconds=(
                window_seconds
            ),
        )

        # -----------------------------------------------------
        # Assertions
        # -----------------------------------------------------

        assert first.allowed is True
        assert first.current == 1
        assert first.remaining == 2

        assert second.allowed is True
        assert second.current == 2
        assert second.remaining == 1

        assert third.allowed is True
        assert third.current == 3
        assert third.remaining == 0

        assert fourth.allowed is False
        assert fourth.current == 4
        assert fourth.remaining == 0

        assert (
            fourth.retry_after
            >= 1
        )

        assert (
            fourth.reset_after
            >= 1
        )

        # -----------------------------------------------------
        # Output
        # -----------------------------------------------------

        print(
            "\n=== REDIS RATE LIMIT TEST ==="
        )

        print(
            "Redis connection confirmed."
        )

        print(
            "First request allowed."
        )

        print(
            "Second request allowed."
        )

        print(
            "Third request allowed."
        )

        print(
            "Fourth request blocked."
        )

        print(
            "Remaining count confirmed."
        )

        print(
            "Retry-After value confirmed."
        )

        print(
            "Reset value confirmed."
        )

        print(
            "Redis rate limiting test "
            "passed successfully."
        )

    finally:
        # -----------------------------------------------------
        # Remove temporary test bucket
        # -----------------------------------------------------

        await limiter.clear_current_bucket(
            scope=scope,
            identifier=identifier,
            window_seconds=(
                window_seconds
            ),
        )

        await client.aclose()


if __name__ == "__main__":
    asyncio.run(
        main()
    )


# uv run python -m tests.test_rate_limiting