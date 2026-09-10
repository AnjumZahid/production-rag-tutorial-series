import asyncio
from uuid import uuid4

from backend.app.auth.service import AuthenticationService
from backend.app.core.exceptions import (
    AuthenticationError,
    ConflictError,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.session import get_session_factory


async def expect_error(
    callback,
    expected_error_type,
    message: str,
) -> None:
    try:
        await callback()
    except expected_error_type:
        print(message)
        return

    raise AssertionError(
        f"Expected {expected_error_type.__name__}, "
        "but no error was raised."
    )


async def main_async() -> None:
    print("=== REAL AUTHENTICATION FLOW TEST ===")

    session_factory = get_session_factory()

    organization_name = f"Test Organization {uuid4().hex[:8]}"
    email = f"auth-test-{uuid4().hex[:8]}@example.com"
    password = "StrongPassword123!"
    wrong_password = "WrongPassword123!"

    async with session_factory() as session:
        service = AuthenticationService(session=session)
        repository = AuthRepository(session)

        registered = await service.register(
            organization_name=organization_name,
            email=email,
            password=password,
            full_name="Auth Test User",
        )

        print("Registration confirmed.")

        assert registered.user.email == email
        assert registered.user.organization_id
        assert registered.access_token
        assert registered.refresh_token

        user = await repository.get_user_by_email(email)
        assert user is not None
        assert user.password_hash != password
        assert "StrongPassword123" not in user.password_hash

        print("Argon2 password hashing confirmed.")

        async def duplicate_register() -> None:
            await service.register(
                organization_name=organization_name,
                email=email,
                password=password,
                full_name="Duplicate User",
            )

        await expect_error(
            duplicate_register,
            ConflictError,
            "Duplicate email rejection confirmed.",
        )

        async def wrong_login() -> None:
            await service.login(
                email=email,
                password=wrong_password,
            )

        await expect_error(
            wrong_login,
            AuthenticationError,
            "Wrong-password rejection confirmed.",
        )

        logged_in = await service.login(
            email=email,
            password=password,
        )

        print("Login confirmed.")

        assert logged_in.user.email == email
        assert logged_in.access_token
        assert logged_in.refresh_token

        refreshed = await service.refresh(
            refresh_token=logged_in.refresh_token,
        )

        print("Refresh-token rotation confirmed.")

        assert refreshed.access_token
        assert refreshed.refresh_token
        assert refreshed.refresh_token != logged_in.refresh_token

        async def reuse_old_refresh_token() -> None:
            await service.refresh(
                refresh_token=logged_in.refresh_token,
            )

        await expect_error(
            reuse_old_refresh_token,
            AuthenticationError,
            "Refresh-token reuse rejection confirmed.",
        )

        current_user = await service.get_current_user(
            user_id=refreshed.user.id,
            organization_id=refreshed.user.organization_id,
        )

        assert current_user.email == email

        print("Current-user lookup confirmed.")

        await service.logout(
            refresh_token=refreshed.refresh_token,
            user_id=refreshed.user.id,
            organization_id=refreshed.user.organization_id,
        )

        print("Logout revocation confirmed.")

        async def refresh_after_logout() -> None:
            await service.refresh(
                refresh_token=refreshed.refresh_token,
            )

        await expect_error(
            refresh_after_logout,
            AuthenticationError,
            "Logged-out refresh token rejection confirmed.",
        )

        await repository.delete_user_auth_data(
            user_id=registered.user.id,
            organization_id=registered.user.organization_id,
        )
        await session.commit()

        print("Cleanup confirmed.")

    print("Real authentication flow test passed successfully.")


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()

# uv run python -m tests.test_real_auth_flow
