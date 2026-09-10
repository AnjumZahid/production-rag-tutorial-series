from fastapi.testclient import (
    TestClient,
)

from backend.app.api.app import (
    create_app,
)
from backend.app.api.dependencies import (
    get_database_session_dependency,
)
from backend.app.rate_limiting.service import (
    get_redis_client,
)


# =============================================================
# Fake database sessions
# =============================================================


class FakeDatabaseSession:
    """
    Healthy database-session replacement.
    """

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> object:
        return object()


class FailingDatabaseSession:
    """
    Unavailable database-session replacement.
    """

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> object:
        raise ConnectionError(
            "Simulated database failure."
        )


# =============================================================
# Fake Redis
# =============================================================


class FakeRedisClient:
    """
    Healthy Redis-client replacement.
    """

    async def ping(
        self,
    ) -> bool:
        return True


# =============================================================
# FastAPI dependency overrides
# =============================================================


async def healthy_db_session():
    yield FakeDatabaseSession()


async def failing_db_session():
    yield FailingDatabaseSession()


def fake_redis_client(
) -> FakeRedisClient:
    return FakeRedisClient()


# =============================================================
# Test
# =============================================================


def main() -> None:
    app = create_app()

    # ---------------------------------------------------------
    # Start with healthy dependencies
    # ---------------------------------------------------------

    app.dependency_overrides[
        get_database_session_dependency
    ] = healthy_db_session

    app.dependency_overrides[
        get_redis_client
    ] = fake_redis_client

    try:
        with TestClient(
            app
        ) as client:

            # =================================================
            # 1. Liveness
            # =================================================

            live_response = (
                client.get(
                    "/api/v1/health/live"
                )
            )

            assert (
                live_response.status_code
                == 200
            )

            assert (
                live_response.json()[
                    "status"
                ]
                == "alive"
            )

            # =================================================
            # 2. Healthy readiness
            # =================================================

            ready_response = (
                client.get(
                    "/api/v1/health/ready"
                )
            )

            assert (
                ready_response.status_code
                == 200
            )

            ready_body = (
                ready_response.json()
            )

            assert (
                ready_body[
                    "status"
                ]
                == "ready"
            )

            # =================================================
            # 3. MySQL status
            # =================================================

            assert (
                ready_body[
                    "checks"
                ][
                    "database"
                ][
                    "status"
                ]
                == "ok"
            )

            # =================================================
            # 4. Redis status
            # =================================================

            assert (
                ready_body[
                    "checks"
                ][
                    "redis"
                ][
                    "status"
                ]
                == "ok"
            )

            # =================================================
            # 5. Simulate database failure
            # =================================================

            app.dependency_overrides[
                get_database_session_dependency
            ] = failing_db_session

            unavailable_response = (
                client.get(
                    "/api/v1/health/ready"
                )
            )

            assert (
                unavailable_response
                .status_code
                == 503
            )

            unavailable_body = (
                unavailable_response.json()
            )

            assert (
                unavailable_body[
                    "status"
                ]
                == "not_ready"
            )

            assert (
                unavailable_body[
                    "checks"
                ][
                    "database"
                ][
                    "status"
                ]
                == "unavailable"
            )

            # =================================================
            # Output
            # =================================================

            print(
                "\n=== HEALTH ENDPOINT TEST ==="
            )

            print(
                "Liveness endpoint confirmed."
            )

            print(
                "Healthy readiness confirmed."
            )

            print(
                "MySQL readiness confirmed."
            )

            print(
                "Redis readiness confirmed."
            )

            print(
                "Unavailable dependency "
                "response confirmed."
            )

            print(
                "Health endpoint test "
                "passed successfully."
            )

    finally:
        app.dependency_overrides.clear()


if __name__ == "__main__":
    main()


# uv run python -m tests.test_health_endpoints