from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.auth import (
    OrganizationRecord,
    RefreshTokenRecord,
    UserRecord,
)
from backend.app.database.models.membership import (
    MembershipRecord,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_organization_by_slug(
        self,
        slug: str,
    ) -> OrganizationRecord | None:
        statement = select(OrganizationRecord).where(
            OrganizationRecord.slug == slug
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_organization_by_id(
        self,
        organization_id: str,
    ) -> OrganizationRecord | None:
        statement = select(
            OrganizationRecord
        ).where(
            OrganizationRecord.id
            == organization_id
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def create_organization(
        self,
        *,
        name: str,
        slug: str,
    ) -> OrganizationRecord:
        organization = OrganizationRecord(
            id=uuid4().hex,
            name=name,
            slug=slug,
        )

        self.session.add(organization)

        return organization

    async def get_user_by_email(
        self,
        email: str,
    ) -> UserRecord | None:
        statement = select(UserRecord).where(
            UserRecord.email == email
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_user_by_id(
        self,
        user_id: str,
    ) -> UserRecord | None:
        statement = select(UserRecord).where(
            UserRecord.id == user_id
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_user_and_organization(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> tuple[UserRecord, OrganizationRecord] | None:
        statement = (
            select(UserRecord, OrganizationRecord)
            .join(
                OrganizationRecord,
                UserRecord.organization_id
                == OrganizationRecord.id,
            )
            .where(
                UserRecord.id == user_id
            )
            .where(
                UserRecord.organization_id
                == organization_id
            )
        )

        result = await self.session.execute(statement)

        row = result.one_or_none()

        if row is None:
            return None

        user, organization = row

        return user, organization

    async def create_user(
        self,
        *,
        organization_id: str,
        email: str,
        password_hash: str,
        full_name: str | None,
        role: str = "owner",
        is_active: bool = True,
    ) -> UserRecord:
        user = UserRecord(
            id=uuid4().hex,
            organization_id=organization_id,
            email=email,
            password_hash=password_hash,
            full_name=full_name,
            role=role,
            is_active=is_active,
        )

        self.session.add(user)

        return user

    async def create_owner_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MembershipRecord:
        """
        Create the initial owner membership for a newly
        registered user.
        """

        membership = MembershipRecord(
            id=uuid4().hex,
            organization_id=organization_id,
            user_id=user_id,
            role="owner",
            is_active=True,
        )

        self.session.add(membership)

        return membership

    async def create_refresh_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        token_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshTokenRecord:
        refresh_token = RefreshTokenRecord(
            id=uuid4().hex,
            user_id=user_id,
            organization_id=organization_id,
            token_id=token_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        self.session.add(refresh_token)

        return refresh_token

    async def get_refresh_token_by_hash_for_update(
        self,
        token_hash: str,
    ) -> RefreshTokenRecord | None:
        statement = (
            select(RefreshTokenRecord)
            .where(
                RefreshTokenRecord.token_hash
                == token_hash
            )
            .with_for_update()
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def revoke_refresh_token(
        self,
        refresh_token: RefreshTokenRecord,
    ) -> RefreshTokenRecord:
        refresh_token.revoked_at = utc_now()

        return refresh_token

    async def delete_user_auth_data(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> None:
        token_statement = select(
            RefreshTokenRecord
        ).where(
            RefreshTokenRecord.user_id == user_id
        )

        token_result = await self.session.execute(
            token_statement
        )

        for token in token_result.scalars().all():
            await self.session.delete(token)

        user_statement = select(UserRecord).where(
            UserRecord.id == user_id
        )

        user_result = await self.session.execute(
            user_statement
        )

        user = user_result.scalar_one_or_none()

        if user is not None:
            await self.session.delete(user)

        organization_statement = select(
            OrganizationRecord
        ).where(
            OrganizationRecord.id == organization_id
        )

        organization_result = await self.session.execute(
            organization_statement
        )

        organization = (
            organization_result.scalar_one_or_none()
        )

        if organization is not None:
            await self.session.delete(organization)