import asyncio
from uuid import uuid4

from backend.app.api.dependencies import (
    OrganizationAccess,
)
from backend.app.auth.roles import (
    OrganizationRole,
)
from backend.app.auth.service import (
    AuthenticationService,
)
from backend.app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)
from backend.app.database.session import (
    get_session_factory,
)
from backend.app.organizations.service import (
    OrganizationService,
)


async def main_async() -> None:
    print(
        "=== ROLE AUTHORIZATION TEST ==="
    )

    session_factory = (
        get_session_factory()
    )

    suffix = uuid4().hex[:8]

    organization_name = (
        f"Role Test Organization "
        f"{suffix}"
    )

    owner_email = (
        f"role-owner-{suffix}"
        f"@example.com"
    )

    member_email = (
        f"role-member-{suffix}"
        f"@example.com"
    )

    admin_email = (
        f"role-admin-{suffix}"
        f"@example.com"
    )

    password = (
        "StrongPassword123!"
    )

    async with session_factory() as session:
        auth_service = (
            AuthenticationService(
                session=session
            )
        )

        auth_repository = (
            AuthRepository(
                session
            )
        )

        membership_repository = (
            MembershipRepository(
                session
            )
        )

        organization_service = (
            OrganizationService(
                session=session
            )
        )

        # ---------------------------------------------
        # 1. Register owner
        # ---------------------------------------------

        owner = await auth_service.register(
            organization_name=(
                organization_name
            ),
            email=owner_email,
            password=password,
            full_name="Role Test Owner",
        )

        organization_id = (
            owner.user.organization_id
        )

        owner_id = owner.user.id

        owner_membership = (
            await membership_repository
            .get_active_membership(
                organization_id=(
                    organization_id
                ),
                user_id=owner_id,
            )
        )

        assert (
            owner_membership
            is not None
        )

        assert (
            owner_membership.role
            == OrganizationRole.OWNER.value
        )

        print(
            "Owner membership confirmed."
        )

        # ---------------------------------------------
        # 2. Owner creates normal member
        # ---------------------------------------------

        member = (
            await organization_service
            .create_member(
                organization_id=(
                    organization_id
                ),
                actor_user_id=owner_id,
                actor_role="owner",
                email=member_email,
                password=password,
                full_name=(
                    "Role Test Member"
                ),
                role="member",
            )
        )

        assert member.role == "member"
        assert member.is_active is True

        print(
            "Owner member creation confirmed."
        )

        # ---------------------------------------------
        # 3. List organization members
        # ---------------------------------------------

        members = (
            await organization_service
            .list_members(
                organization_id=(
                    organization_id
                )
            )
        )

        assert any(
            item.email == member_email
            for item in members
        )

        print(
            "Member listing confirmed."
        )

        # ---------------------------------------------
        # 4. Change member -> viewer
        # ---------------------------------------------

        updated_member = (
            await organization_service
            .change_member_role(
                organization_id=(
                    organization_id
                ),
                actor_user_id=owner_id,
                actor_role="owner",
                membership_id=(
                    member.membership_id
                ),
                role="viewer",
            )
        )

        assert (
            updated_member.role
            == "viewer"
        )

        print(
            "Member role update confirmed."
        )

        # ---------------------------------------------
        # 5. Owner creates admin
        # ---------------------------------------------

        admin = (
            await organization_service
            .create_member(
                organization_id=(
                    organization_id
                ),
                actor_user_id=owner_id,
                actor_role="owner",
                email=admin_email,
                password=password,
                full_name=(
                    "Role Test Admin"
                ),
                role="admin",
            )
        )

        assert admin.role == "admin"

        print(
            "Owner admin creation confirmed."
        )

        # ---------------------------------------------
        # 6. Admin cannot create another admin
        # ---------------------------------------------

        try:
            await organization_service.create_member(
                organization_id=(
                    organization_id
                ),
                actor_user_id=(
                    admin.user_id
                ),
                actor_role="admin",
                email=(
                    f"blocked-admin-"
                    f"{suffix}@example.com"
                ),
                password=password,
                full_name="Blocked Admin",
                role="admin",
            )

            raise AssertionError(
                "Admin should not be able "
                "to create another admin."
            )

        except AuthorizationError:
            pass

        print(
            "Admin restriction confirmed."
        )

        # ---------------------------------------------
        # 7. Owner role cannot be changed
        # ---------------------------------------------

        try:
            await organization_service.change_member_role(
                organization_id=(
                    organization_id
                ),
                actor_user_id=(
                    admin.user_id
                ),
                actor_role="admin",
                membership_id=(
                    owner_membership.id
                ),
                role="member",
            )

            raise AssertionError(
                "Owner role should be protected."
            )

        except AuthorizationError:
            pass

        print(
            "Owner role protection confirmed."
        )

        # ---------------------------------------------
        # 8. Deactivate member
        # ---------------------------------------------

        deactivated = (
            await organization_service
            .deactivate_member(
                organization_id=(
                    organization_id
                ),
                actor_user_id=owner_id,
                actor_role="owner",
                membership_id=(
                    member.membership_id
                ),
            )
        )

        assert (
            deactivated.is_active
            is False
        )

        print(
            "Member deactivation confirmed."
        )

        # ---------------------------------------------
        # 9. Deactivated member cannot login
        # ---------------------------------------------

        try:
            await auth_service.login(
                email=member_email,
                password=password,
            )

            raise AssertionError(
                "Inactive member should "
                "not be able to login."
            )

        except AuthenticationError:
            pass

        print(
            "Inactive-member login "
            "blocking confirmed."
        )

        # ---------------------------------------------
        # 10. Owner cannot deactivate themselves
        # ---------------------------------------------

        try:
            await organization_service.deactivate_member(
                organization_id=(
                    organization_id
                ),
                actor_user_id=owner_id,
                actor_role="owner",
                membership_id=(
                    owner_membership.id
                ),
            )

            raise AssertionError(
                "Owner should not be able "
                "to deactivate themselves."
            )

        except AuthorizationError:
            pass

        print(
            "Self-deactivation protection confirmed."
        )

        # ---------------------------------------------
        # 11. Cleanup
        # ---------------------------------------------

        await auth_repository.delete_user_auth_data(
            user_id=owner_id,
            organization_id=(
                organization_id
            ),
        )

        await session.commit()

        print(
            "Temporary role-test records "
            "cleaned up."
        )

    print(
        "Role authorization test "
        "passed successfully."
    )


def main() -> None:
    asyncio.run(
        main_async()
    )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_role_authorization