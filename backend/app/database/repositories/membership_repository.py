from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.membership import (
    MembershipRecord,
)


class MembershipRepository:
    """Database operations for organization memberships."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MembershipRecord | None:
        """
        Get a membership regardless of whether it is active.
        """

        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .where(
                MembershipRecord.user_id == user_id
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def get_active_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MembershipRecord | None:
        """
        Get an active membership for a user inside an organization.
        """

        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .where(
                MembershipRecord.user_id == user_id
            )
            .where(
                MembershipRecord.is_active.is_(True)
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_active_memberships_for_user(
        self,
        *,
        user_id: str,
    ) -> list[MembershipRecord]:
        """
        List all active organization memberships for a user.
        """

        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.user_id == user_id
            )
            .where(
                MembershipRecord.is_active.is_(True)
            )
            .order_by(
                MembershipRecord.created_at.asc()
            )
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())