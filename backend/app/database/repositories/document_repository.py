from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    DatabaseError,
    DocumentNotFoundError,
    DuplicateDocumentError,
)
from backend.app.database.enums import DocumentStatus
from backend.app.database.models import (
    DocumentChunkRecord,
    DocumentRecord,
)


@dataclass(frozen=True, slots=True)
class ChunkReference:
    """
    Information required to connect one MySQL chunk record
    with one vector stored in Chroma.
    """

    chunk_id: str
    vector_id: str
    page_number: int
    chunk_index: int


class DocumentRepository:
    """
    Handles MySQL operations for documents and chunk references.

    The repository flushes changes to the session but does not commit.
    The service or API layer controls the transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
    ) -> DocumentRecord | None:
        """Get one document while enforcing organization and user ownership."""

        statement = select(DocumentRecord).where(
            DocumentRecord.id == document_id,
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.user_id == user_id,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_hash(
        self,
        *,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
        file_hash: str,
    ) -> DocumentRecord | None:
        """
        Find whether the same user already uploaded the same file
        into the same knowledge base.
        """

        statement = select(DocumentRecord).where(
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.user_id == user_id,
            DocumentRecord.knowledge_base_id == knowledge_base_id,
            DocumentRecord.file_hash == file_hash,
        )

        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def create_document(
        self,
        *,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
        filename: str,
        file_hash: str,
        file_size_bytes: int,
        total_pages: int | None = None,
    ) -> DocumentRecord:
        """
        Create a pending document record.

        The database unique constraint provides final protection
        against concurrent duplicate uploads.
        """

        document = DocumentRecord(
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            filename=filename,
            file_hash=file_hash,
            file_size_bytes=file_size_bytes,
            total_pages=total_pages,
            status=DocumentStatus.PENDING.value,
        )

        try:
            async with self.session.begin_nested():
                self.session.add(document)
                await self.session.flush()
        except IntegrityError as exc:
            raise DuplicateDocumentError(
                details={
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "file_hash": file_hash,
                }
            ) from exc

        return document

    async def add_chunk_references(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
        chunk_references: Sequence[ChunkReference],
    ) -> list[DocumentChunkRecord]:
        """Store MySQL references to vectors already stored in Chroma."""

        document = await self.get_by_id(
            document_id=document_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        if document is None:
            raise DocumentNotFoundError(
                details={
                    "document_id": document_id,
                }
            )

        if not chunk_references:
            return []

        records = [
            DocumentChunkRecord(
                document_record_id=document.id,
                chunk_id=reference.chunk_id,
                vector_id=reference.vector_id,
                page_number=reference.page_number,
                chunk_index=reference.chunk_index,
            )
            for reference in chunk_references
        ]

        try:
            self.session.add_all(records)
            document.chunk_count += len(records)
            await self.session.flush()
        except IntegrityError as exc:
            raise DatabaseError(
                message="One or more chunk references could not be stored.",
                details={
                    "document_id": document_id,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        return records

    async def update_status(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
        status: DocumentStatus,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        embedding_dimension: int | None = None,
        vector_store_provider: str | None = None,
        total_pages: int | None = None,
        error_message: str | None = None,
    ) -> DocumentRecord:
        """Update document ingestion status and processing information."""

        document = await self.get_by_id(
            document_id=document_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        if document is None:
            raise DocumentNotFoundError(
                details={
                    "document_id": document_id,
                }
            )

        document.status = status.value

        if embedding_provider is not None:
            document.embedding_provider = embedding_provider

        if embedding_model is not None:
            document.embedding_model = embedding_model

        if embedding_dimension is not None:
            document.embedding_dimension = embedding_dimension

        if vector_store_provider is not None:
            document.vector_store_provider = vector_store_provider

        if total_pages is not None:
            document.total_pages = total_pages

        document.error_message = error_message

        await self.session.flush()
        return document

    async def list_documents(
        self,
        *,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        """
        List documents owned by one user.

        The optional knowledge_base_id limits results to one knowledge base.
        """

        statement = select(DocumentRecord).where(
            DocumentRecord.organization_id == organization_id,
            DocumentRecord.user_id == user_id,
        )

        if knowledge_base_id is not None:
            statement = statement.where(
                DocumentRecord.knowledge_base_id == knowledge_base_id
            )

        statement = (
            statement
            .order_by(DocumentRecord.created_at.desc())
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_document_record(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
    ) -> bool:
        """
        Delete a document and its MySQL chunk references.

        Important:
        The service layer must delete the corresponding vectors from
        Chroma before calling this method.
        """

        document = await self.get_by_id(
            document_id=document_id,
            organization_id=organization_id,
            user_id=user_id,
        )

        if document is None:
            return False

        await self.session.delete(document)
        await self.session.flush()

        return True