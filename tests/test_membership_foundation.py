import asyncio
from uuid import uuid4

from backend.app.auth.service import (
    AuthenticationService,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.session import (
    get_session_factory,
)


async def main_async() -> None:
    print(
        "=== MEMBERSHIP FOUNDATION TEST ==="
    )

    session_factory = get_session_factory()

    organization_name = (
        f"Membership Test Organization "
        f"{uuid4().hex[:8]}"
    )

    email = (
        f"membership-test-"
        f"{uuid4().hex[:8]}"
        f"@example.com"
    )

    password = "StrongPassword123!"

    async with session_factory() as session:
        auth_repository = AuthRepository(
            session
        )

        membership_repository = (
            MembershipRepository(session)
        )

        service = AuthenticationService(
            session=session
        )

        # -------------------------------------------------
        # 1. Register organization owner
        # -------------------------------------------------

        registered = await service.register(
            organization_name=organization_name,
            email=email,
            password=password,
            full_name="Membership Test Owner",
        )

        print(
            "Organization registration confirmed."
        )

        assert registered.user.id
        assert registered.user.organization_id
        assert registered.user.role == "owner"
        assert registered.user.is_active is True

        print(
            "Owner user registration confirmed."
        )

        # -------------------------------------------------
        # 2. Get membership
        # -------------------------------------------------

        membership = (
            await membership_repository.get_membership(
                organization_id=(
                    registered.user.organization_id
                ),
                user_id=registered.user.id,
            )
        )

        assert membership is not None

        print(
            "Owner membership creation confirmed."
        )

        assert (
            membership.organization_id
            == registered.user.organization_id
        )

        assert (
            membership.user_id
            == registered.user.id
        )

        assert membership.role == "owner"
        assert membership.is_active is True

        # -------------------------------------------------
        # 3. Get active membership
        # -------------------------------------------------

        active_membership = (
            await membership_repository
            .get_active_membership(
                organization_id=(
                    registered.user.organization_id
                ),
                user_id=registered.user.id,
            )
        )

        assert active_membership is not None

        assert (
            active_membership.id
            == membership.id
        )

        assert (
            active_membership.is_active
            is True
        )

        print(
            "Active membership lookup confirmed."
        )

        # -------------------------------------------------
        # 4. List active memberships
        # -------------------------------------------------

        memberships = (
            await membership_repository
            .list_active_memberships_for_user(
                user_id=registered.user.id
            )
        )

        assert len(memberships) >= 1

        matching_memberships = [
            item
            for item in memberships
            if (
                item.organization_id
                == registered.user.organization_id
            )
        ]

        assert len(
            matching_memberships
        ) == 1

        assert (
            matching_memberships[0].role
            == "owner"
        )

        print(
            "Membership listing confirmed."
        )

        # -------------------------------------------------
        # 5. Verify organization/user relationship
        # -------------------------------------------------

        user = (
            await auth_repository.get_user_by_email(
                email
            )
        )

        assert user is not None

        assert (
            user.organization_id
            == membership.organization_id
        )

        print(
            "Organization-user relationship confirmed."
        )

        # -------------------------------------------------
        # 6. Cleanup
        # -------------------------------------------------

        await auth_repository.delete_user_auth_data(
            user_id=registered.user.id,
            organization_id=(
                registered.user.organization_id
            ),
        )

        await session.commit()

        print(
            "Temporary membership records cleaned up."
        )

    print(
        "Membership foundation test passed successfully."
    )


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()


# uv run python -m tests.test_membership_foundation