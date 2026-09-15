from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database.base import Base


class DocumentRecord(Base):
    """
    Registry entry for one uploaded document.

    This table is used to:
    - detect duplicate uploads through file_hash
    - identify document ownership
    - track ingestion status
    - remember which embedding model was used
    - reconnect users to previously stored vectors
    """

    __tablename__ = "document_records"

    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "knowledge_base_id",
            "file_hash",
            name="uq_document_owner_knowledge_base_hash",
        ),
        Index(
            "ix_document_owner_knowledge_base",
            "organization_id",
            "user_id",
            "knowledge_base_id",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    organization_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    user_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    file_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )

    total_pages: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    chunk_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
        server_default="pending",
        index=True,
    )

    embedding_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    embedding_model: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    embedding_dimension: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    vector_store_provider: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    chunks: Mapped[list["DocumentChunkRecord"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class DocumentChunkRecord(Base):
    """
    MySQL reference to one vector-store chunk.

    The actual vector remains in Chroma.
    MySQL stores its chunk_id so it can later be tracked or deleted.
    """

    __tablename__ = "document_chunk_records"

    __table_args__ = (
        UniqueConstraint(
            "vector_id",
            name="uq_document_chunk_vector_id",
        ),

        Index(
            "ix_document_chunk_document_page",
            "document_record_id",
            "page_number",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    document_record_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey(
            "document_records.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    chunk_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    vector_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    page_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["DocumentRecord"] = relationship(
        back_populates="chunks",
    )
