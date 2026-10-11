from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.passwords import (
    PasswordService,
    password_service,
)
from backend.app.auth.roles import OrganizationRole
from backend.app.core.exceptions import (
    AuthorizationError,
    ConflictError,
)
from backend.app.database.models.auth import (
    OrganizationRecord,
    UserRecord,
)
from backend.app.database.models.membership import (
    MembershipRecord,
)
from backend.app.database.repositories.auth_repository import (
    AuthRepository,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)


@dataclass(frozen=True, slots=True)
class OrganizationSummary:
    """
    Public organization information returned by
    the organization service.
    """

    id: str
    name: str
    slug: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class OrganizationMember:
    """
    Public organization-member information returned
    by the organization service.
    """

    membership_id: str
    user_id: str
    email: str
    full_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class OrganizationService:
    """
    Business logic for organization and
    organization-member management.

    Authorization rules:

    Owner:
        - Can create admin/member/viewer
        - Can change member/admin roles
        - Can deactivate members/admins

    Admin:
        - Can create member/viewer
        - Cannot create another admin
        - Cannot modify another admin
        - Cannot assign admin role
        - Cannot modify owner

    Owner protection:
        - Owner role cannot be assigned
        - Owner role cannot be changed
        - Owner cannot be deactivated

    Self protection:
        - Actor cannot change own role
        - Actor cannot deactivate themselves
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        membership_repository: MembershipRepository | None = None,
        auth_repository: AuthRepository | None = None,
        passwords: PasswordService = password_service,
    ) -> None:
        self.session = session

        self.memberships = (
            membership_repository
            or MembershipRepository(session)
        )

        self.auth = (
            auth_repository
            or AuthRepository(session)
        )

        self.passwords = passwords

    # ---------------------------------------------------------
    # Current organization
    # ---------------------------------------------------------

    async def get_current_organization(
        self,
        *,
        organization_id: str,
    ) -> OrganizationSummary:
        """
        Return the current authenticated organization.
        """

        organization = (
            await self.auth.get_organization_by_id(
                organization_id
            )
        )

        if organization is None:
            raise AuthorizationError(
                message=(
                    "The authenticated organization "
                    "could not be found."
                )
            )

        return self._public_organization(
            organization
        )

    # ---------------------------------------------------------
    # List members
    # ---------------------------------------------------------

    async def list_members(
        self,
        *,
        organization_id: str,
    ) -> list[OrganizationMember]:
        """
        Return all memberships belonging to
        an organization.
        """

        rows = (
            await self.memberships
            .list_organization_members(
                organization_id=organization_id
            )
        )

        return [
            self._public_member(
                membership,
                user,
            )
            for membership, user in rows
        ]

    # ---------------------------------------------------------
    # Create member
    # ---------------------------------------------------------

    async def create_member(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        actor_role: str,
        email: str,
        password: str,
        full_name: str | None,
        role: str,
    ) -> OrganizationMember:
        """
        Create a new user and organization membership.

        Allowed actors:
            owner
            admin

        Restrictions:
            owner role cannot be created here
            admin cannot create another admin
            duplicate email is rejected
        """

        actor = self._normalize_role(
            actor_role
        )

        requested_role = self._normalize_role(
            role
        )

        # -------------------------------------------------
        # Actor must be owner or admin
        # -------------------------------------------------

        if actor not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        }:
            raise AuthorizationError(
                message=(
                    "Only organization owners and admins "
                    "can create members."
                )
            )

        # -------------------------------------------------
        # Owner cannot be created through member endpoint
        # -------------------------------------------------

        if (
            requested_role
            == OrganizationRole.OWNER
        ):
            raise AuthorizationError(
                message=(
                    "The owner role cannot be assigned "
                    "through the member-management endpoint."
                )
            )

        # -------------------------------------------------
        # Admin cannot create another admin
        # -------------------------------------------------

        if (
            actor == OrganizationRole.ADMIN
            and requested_role
            == OrganizationRole.ADMIN
        ):
            raise AuthorizationError(
                message=(
                    "An admin cannot create another admin."
                )
            )

        # -------------------------------------------------
        # Normalize email
        # -------------------------------------------------

        normalized_email = (
            email.strip().lower()
        )

        # -------------------------------------------------
        # Duplicate user check
        # -------------------------------------------------

        existing_user = (
            await self.auth.get_user_by_email(
                normalized_email
            )
        )

        if existing_user is not None:
            raise ConflictError(
                message=(
                    "A user with this email already exists."
                )
            )

        # -------------------------------------------------
        # Hash password
        # -------------------------------------------------

        password_hash = (
            self.passwords.hash_password(
                password
            )
        )

        # -------------------------------------------------
        # Create user
        #
        # UserRecord.role is kept synchronized for
        # compatibility with the existing auth model.
        #
        # MembershipRecord.role remains the authorization
        # source of truth.
        # -------------------------------------------------

        user = await self.auth.create_user(
            organization_id=organization_id,
            email=normalized_email,
            password_hash=password_hash,
            full_name=(
                full_name.strip()
                if full_name
                else None
            ),
            role=requested_role.value,
            is_active=True,
        )

        await self.session.flush()

        # -------------------------------------------------
        # Create organization membership
        # -------------------------------------------------

        membership = (
            await self.memberships.create_membership(
                organization_id=organization_id,
                user_id=user.id,
                role=requested_role.value,
            )
        )

        # -------------------------------------------------
        # MissingGreenlet protection
        #
        # created_at / updated_at may be DB-generated.
        # Refresh the membership before accessing them.
        # -------------------------------------------------

        await self.session.flush()

        await self.session.refresh(
            membership
        )

        # Build response before commit so all values are
        # already loaded while the session is active.
        member_response = self._public_member(
            membership,
            user,
        )

        await self.session.commit()

        return member_response

    # ---------------------------------------------------------
    # Change member role
    # ---------------------------------------------------------

    async def change_member_role(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        actor_role: str,
        membership_id: str,
        role: str,
    ) -> OrganizationMember:
        """
        Change an organization's membership role.

        Rules:
            owner role cannot be assigned
            owner's role cannot be modified
            actor cannot modify own role
            admin cannot modify another admin
            admin cannot assign admin role
        """

        actor = self._normalize_role(
            actor_role
        )

        requested_role = self._normalize_role(
            role
        )

        # -------------------------------------------------
        # Only owner/admin should reach this service action
        # -------------------------------------------------

        if actor not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        }:
            raise AuthorizationError(
                message=(
                    "Only organization owners and admins "
                    "can change member roles."
                )
            )

        # -------------------------------------------------
        # Owner role cannot be assigned
        # -------------------------------------------------

        if (
            requested_role
            == OrganizationRole.OWNER
        ):
            raise AuthorizationError(
                message=(
                    "The owner role cannot be assigned."
                )
            )

        # -------------------------------------------------
        # Load target membership with row lock
        # -------------------------------------------------

        membership = (
            await self.memberships
            .get_membership_for_update(
                membership_id=membership_id,
                organization_id=organization_id,
            )
        )

        if membership is None:
            raise AuthorizationError(
                message=(
                    "The requested organization membership "
                    "was not found."
                )
            )

        # -------------------------------------------------
        # Owner role cannot be changed
        # -------------------------------------------------

        if (
            membership.role
            == OrganizationRole.OWNER.value
        ):
            raise AuthorizationError(
                message=(
                    "The organization owner's role "
                    "cannot be changed."
                )
            )

        # -------------------------------------------------
        # Actor cannot modify own role
        # -------------------------------------------------

        if (
            membership.user_id
            == actor_user_id
        ):
            raise AuthorizationError(
                message=(
                    "You cannot change your own "
                    "organization role."
                )
            )

        target_role = self._normalize_role(
            membership.role
        )

        # -------------------------------------------------
        # Admin restrictions
        # -------------------------------------------------

        if actor == OrganizationRole.ADMIN:

            # Admin cannot modify another admin
            if (
                target_role
                == OrganizationRole.ADMIN
            ):
                raise AuthorizationError(
                    message=(
                        "An admin cannot modify "
                        "another admin."
                    )
                )

            # Admin cannot promote someone to admin
            if (
                requested_role
                == OrganizationRole.ADMIN
            ):
                raise AuthorizationError(
                    message=(
                        "An admin cannot assign "
                        "the admin role."
                    )
                )

        # -------------------------------------------------
        # Find corresponding user
        # -------------------------------------------------

        user = await self.auth.get_user_by_id(
            membership.user_id
        )

        if user is None:
            raise AuthorizationError(
                message=(
                    "The user associated with this "
                    "membership could not be found."
                )
            )

        # -------------------------------------------------
        # Update membership role
        # -------------------------------------------------

        await self.memberships.set_role(
            membership=membership,
            role=requested_role.value,
        )

        # -------------------------------------------------
        # Keep UserRecord.role synchronized
        #
        # Authorization still uses MembershipRecord.role.
        # -------------------------------------------------

        user.role = requested_role.value

        await self.session.flush()

        await self.session.refresh(
            membership
        )

        response = self._public_member(
            membership,
            user,
        )

        await self.session.commit()

        return response

    # ---------------------------------------------------------
    # Deactivate member
    # ---------------------------------------------------------

    async def deactivate_member(
        self,
        *,
        organization_id: str,
        actor_user_id: str,
        actor_role: str,
        membership_id: str,
    ) -> OrganizationMember:
        """
        Deactivate an organization membership.

        Rules:
            actor cannot deactivate themselves
            owner cannot be deactivated
            admin cannot deactivate another admin
        """

        actor = self._normalize_role(
            actor_role
        )

        # -------------------------------------------------
        # Only owner/admin can deactivate members
        # -------------------------------------------------

        if actor not in {
            OrganizationRole.OWNER,
            OrganizationRole.ADMIN,
        }:
            raise AuthorizationError(
                message=(
                    "Only organization owners and admins "
                    "can deactivate members."
                )
            )

        # -------------------------------------------------
        # Load target membership with row lock
        # -------------------------------------------------

        membership = (
            await self.memberships
            .get_membership_for_update(
                membership_id=membership_id,
                organization_id=organization_id,
            )
        )

        if membership is None:
            raise AuthorizationError(
                message=(
                    "The requested organization membership "
                    "was not found."
                )
            )

        # -------------------------------------------------
        # Actor cannot deactivate themselves
        # -------------------------------------------------

        if (
            membership.user_id
            == actor_user_id
        ):
            raise AuthorizationError(
                message=(
                    "You cannot deactivate your own "
                    "organization membership."
                )
            )

        target_role = self._normalize_role(
            membership.role
        )

        # -------------------------------------------------
        # Owner cannot be deactivated
        # -------------------------------------------------

        if (
            target_role
            == OrganizationRole.OWNER
        ):
            raise AuthorizationError(
                message=(
                    "The organization owner cannot "
                    "be deactivated."
                )
            )

        # -------------------------------------------------
        # Admin cannot deactivate another admin
        # -------------------------------------------------

        if (
            actor == OrganizationRole.ADMIN
            and target_role
            == OrganizationRole.ADMIN
        ):
            raise AuthorizationError(
                message=(
                    "An admin cannot deactivate "
                    "another admin."
                )
            )

        # -------------------------------------------------
        # Find corresponding user
        # -------------------------------------------------

        user = await self.auth.get_user_by_id(
            membership.user_id
        )

        if user is None:
            raise AuthorizationError(
                message=(
                    "The user associated with this "
                    "membership could not be found."
                )
            )

        # -------------------------------------------------
        # Deactivate membership
        # -------------------------------------------------

        await self.memberships.deactivate_membership(
            membership=membership,
        )

        await self.session.flush()

        await self.session.refresh(
            membership
        )

        response = self._public_member(
            membership,
            user,
        )

        await self.session.commit()

        return response

    # ---------------------------------------------------------
    # Internal helpers
    # ---------------------------------------------------------

    def _normalize_role(
        self,
        role: str | OrganizationRole,
    ) -> OrganizationRole:
        """
        Convert string role into OrganizationRole.
        """

        try:
            return OrganizationRole(
                role
            )

        except ValueError as exc:
            raise AuthorizationError(
                message=(
                    "The requested organization role "
                    "is invalid."
                )
            ) from exc

    def _public_organization(
        self,
        organization: OrganizationRecord,
    ) -> OrganizationSummary:
        """
        Convert OrganizationRecord into safe
        organization response object.
        """

        return OrganizationSummary(
            id=organization.id,
            name=organization.name,
            slug=organization.slug,
            created_at=organization.created_at,
        )

    def _public_member(
        self,
        membership: MembershipRecord,
        user: UserRecord,
    ) -> OrganizationMember:
        """
        Combine MembershipRecord and UserRecord into
        public organization-member response.
        """

        return OrganizationMember(
            membership_id=membership.id,
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            role=membership.role,
            is_active=membership.is_active,
            created_at=membership.created_at,
            updated_at=membership.updated_at,
        )