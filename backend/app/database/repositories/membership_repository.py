from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database.models.auth import (
    UserRecord,
)
from backend.app.database.models.membership import (
    MembershipRecord,
)


class MembershipRepository:
    """Database operations for organization memberships."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def create_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
        role: str,
    ) -> MembershipRecord:
        membership = MembershipRecord(
            id=uuid4().hex,
            organization_id=organization_id,
            user_id=user_id,
            role=role,
            is_active=True,
        )

        self.session.add(membership)

        await self.session.flush()

        return membership

    async def get_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MembershipRecord | None:
        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .where(
                MembershipRecord.user_id
                == user_id
            )
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_active_membership(
        self,
        *,
        organization_id: str,
        user_id: str,
    ) -> MembershipRecord | None:
        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .where(
                MembershipRecord.user_id
                == user_id
            )
            .where(
                MembershipRecord.is_active.is_(True)
            )
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def get_membership_for_update(
        self,
        *,
        membership_id: str,
        organization_id: str,
    ) -> MembershipRecord | None:
        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.id
                == membership_id
            )
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .with_for_update()
        )

        result = await self.session.execute(
            statement
        )

        return result.scalar_one_or_none()

    async def list_active_memberships_for_user(
        self,
        *,
        user_id: str,
    ) -> list[MembershipRecord]:
        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.user_id
                == user_id
            )
            .where(
                MembershipRecord.is_active.is_(True)
            )
            .order_by(
                MembershipRecord.created_at.asc()
            )
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def list_user_memberships(
        self,
        *,
        user_id: str,
    ) -> list[MembershipRecord]:
        statement = (
            select(MembershipRecord)
            .where(
                MembershipRecord.user_id
                == user_id
            )
            .order_by(
                MembershipRecord.created_at.asc()
            )
        )

        result = await self.session.execute(
            statement
        )

        return list(
            result.scalars().all()
        )

    async def list_organization_members(
        self,
        *,
        organization_id: str,
    ) -> list[
        tuple[
            MembershipRecord,
            UserRecord,
        ]
    ]:
        statement = (
            select(
                MembershipRecord,
                UserRecord,
            )
            .join(
                UserRecord,
                UserRecord.id
                == MembershipRecord.user_id,
            )
            .where(
                MembershipRecord.organization_id
                == organization_id
            )
            .order_by(
                MembershipRecord.created_at.asc()
            )
        )

        result = await self.session.execute(
            statement
        )

        return [
            (membership, user)
            for membership, user
            in result.all()
        ]

    async def set_role(
        self,
        *,
        membership: MembershipRecord,
        role: str,
    ) -> MembershipRecord:
        membership.role = role

        await self.session.flush()

        return membership

    async def deactivate_membership(
        self,
        *,
        membership: MembershipRecord,
    ) -> MembershipRecord:
        membership.is_active = False

        await self.session.flush()

        return membership