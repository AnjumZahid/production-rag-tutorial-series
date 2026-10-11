from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MembershipRecord(Base):
    """
    Represents a user's membership inside an organization.

    A user can have at most one membership record for a given
    organization.
    """

    __tablename__ = "organization_membership_records"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "organization_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey(
            "user_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            name="uq_organization_membership_org_user",
        ),
        Index(
            "ix_organization_membership_user_active",
            "user_id",
            "is_active",
        ),
        Index(
            "ix_organization_membership_org_active",
            "organization_id",
            "is_active",
        ),
    )