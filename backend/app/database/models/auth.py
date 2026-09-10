from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrganizationRecord(Base):
    __tablename__ = "organization_records"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    users: Mapped[list["UserRecord"]] = relationship(
        "UserRecord",
        back_populates="organization",
        cascade="all, delete-orphan",
    )


class UserRecord(Base):
    __tablename__ = "user_records"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organization_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )

    full_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(50),
        default="owner",
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

    organization: Mapped[OrganizationRecord] = relationship(
        "OrganizationRecord",
        back_populates="users",
    )

    refresh_tokens: Mapped[list["RefreshTokenRecord"]] = relationship(
        "RefreshTokenRecord",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint(
            "email",
            name="uq_user_records_email",
        ),
        Index(
            "ix_user_records_organization_email",
            "organization_id",
            "email",
        ),
    )


class RefreshTokenRecord(Base):
    __tablename__ = "refresh_token_records"

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("user_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    organization_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("organization_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )

    user: Mapped[UserRecord] = relationship(
        "UserRecord",
        back_populates="refresh_tokens",
    )

    __table_args__ = (
        Index(
            "ix_refresh_token_records_user_org",
            "user_id",
            "organization_id",
        ),
    )