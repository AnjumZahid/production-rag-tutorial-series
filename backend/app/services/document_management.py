import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    AppError,
    DocumentDeletionError,
    DocumentNotFoundError,
)
from backend.app.database.enums import (
    DocumentStatus,
)
from backend.app.database.models import (
    DocumentRecord,
)
from backend.app.database.repositories import (
    DocumentRepository,
)


class VectorDeletionProtocol(Protocol):
    """
    Minimal vector-store interface required
    for document deletion.
    """

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:
        """
        Delete vectors using their stored vector IDs.
        """
        ...


@dataclass(frozen=True, slots=True)
class DocumentView:
    """
    Safe API-facing representation of a document.

    Internal ownership information such as organization_id,
    user_id and file_hash is intentionally not exposed.
    """

    id: str
    knowledge_base_id: str
    filename: str
    status: str
    file_size_bytes: int
    total_pages: int | None
    chunk_count: int
    embedding_provider: str | None
    embedding_model: str | None
    embedding_dimension: int | None
    vector_store_provider: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DocumentListResult:
    """
    Paginated document-list result returned by
    the service layer.
    """

    documents: tuple[DocumentView, ...]
    total: int
    offset: int
    limit: int


class DocumentManagementService:
    """
    Business logic for listing, reading and deleting
    authenticated user-owned documents.

    All repository calls remain scoped by:

        organization_id
        user_id
        document_id / knowledge_base_id

    This prevents cross-tenant and cross-user access.
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: DocumentRepository,
    ) -> None:
        self.session = session
        self.repository = repository

    # ---------------------------------------------------------
    # Document conversion
    # ---------------------------------------------------------

    @staticmethod
    def _to_view(
        document: DocumentRecord,
    ) -> DocumentView:
        """
        Convert an ORM DocumentRecord into a safe,
        immutable service-layer view.
        """

        return DocumentView(
            id=document.id,
            knowledge_base_id=(
                document.knowledge_base_id
            ),
            filename=document.filename,
            status=document.status,
            file_size_bytes=(
                document.file_size_bytes
            ),
            total_pages=document.total_pages,
            chunk_count=document.chunk_count,
            embedding_provider=(
                document.embedding_provider
            ),
            embedding_model=(
                document.embedding_model
            ),
            embedding_dimension=(
                document.embedding_dimension
            ),
            vector_store_provider=(
                document.vector_store_provider
            ),
            error_message=(
                document.error_message
            ),
            created_at=document.created_at,
            updated_at=document.updated_at,
        )

    # ---------------------------------------------------------
    # List documents
    # ---------------------------------------------------------

    async def list_documents(
        self,
        *,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str | None,
        offset: int,
        limit: int,
    ) -> DocumentListResult:
        """
        Return one paginated list of user-owned documents.
        """

        normalized_knowledge_base_id = None

        if knowledge_base_id is not None:
            normalized_knowledge_base_id = (
                knowledge_base_id.strip()
            )

        documents = (
            await self.repository.list_documents(
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=(
                    normalized_knowledge_base_id
                ),
                offset=offset,
                limit=limit,
            )
        )

        total = (
            await self.repository.count_documents(
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=(
                    normalized_knowledge_base_id
                ),
            )
        )

        return DocumentListResult(
            documents=tuple(
                self._to_view(document)
                for document in documents
            ),
            total=total,
            offset=offset,
            limit=limit,
        )

    # ---------------------------------------------------------
    # Get document
    # ---------------------------------------------------------

    async def get_document(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
    ) -> DocumentView:
        """
        Return one document only when it belongs to the
        authenticated organization and user.
        """

        document = (
            await self.repository.get_by_id(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
            )
        )

        if document is None:
            raise DocumentNotFoundError(
                details={
                    "document_id": document_id,
                }
            )

        return self._to_view(
            document
        )

    # ---------------------------------------------------------
    # Delete document
    # ---------------------------------------------------------

    async def delete_document(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
        vector_store: VectorDeletionProtocol,
    ) -> None:
        """
        Completely delete one document.

        Deletion order:

        1. Lock MySQL document row.
        2. Load vector IDs.
        3. Mark document as deleting.
        4. Delete vectors from vector store.
        5. Delete document from MySQL.
        6. MySQL cascade deletes chunk references.
        7. Commit transaction.
        """

        document = (
            await self.repository
            .get_by_id_for_update(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
            )
        )

        if document is None:
            raise DocumentNotFoundError(
                details={
                    "document_id": document_id,
                }
            )

        try:
            # -------------------------------------------------
            # Load vector IDs while MySQL references still exist
            # -------------------------------------------------

            vector_ids = (
                await self.repository.list_vector_ids(
                    document_id=document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )
            )

            # -------------------------------------------------
            # Mark document as deleting
            # -------------------------------------------------

            await self.repository.update_status(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                status=DocumentStatus.DELETING,
                error_message=None,
            )

            # -------------------------------------------------
            # Delete external vectors first
            #
            # Chroma operation is synchronous, therefore
            # move it away from the FastAPI event loop.
            # -------------------------------------------------

            if vector_ids:
                await asyncio.to_thread(
                    vector_store.delete_chunks,
                    vector_ids,
                )

            # -------------------------------------------------
            # Delete MySQL document
            #
            # document_chunk_records are removed through
            # the existing ON DELETE CASCADE relationship.
            # -------------------------------------------------

            deleted = (
                await self.repository
                .delete_document_record(
                    document_id=document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )
            )

            if not deleted:
                raise DocumentNotFoundError(
                    details={
                        "document_id": (
                            document_id
                        ),
                    }
                )

            # -------------------------------------------------
            # Commit complete deletion
            # -------------------------------------------------

            await self.session.commit()

        # -----------------------------------------------------
        # Known application error
        # -----------------------------------------------------

        except AppError:
            await self.session.rollback()
            raise

        # -----------------------------------------------------
        # Unexpected error
        #
        # Never expose the raw internal exception message.
        # -----------------------------------------------------

        except Exception as exc:
            await self.session.rollback()

            raise DocumentDeletionError(
                details={
                    "document_id": document_id,
                    "error_type": (
                        type(exc).__name__
                    ),
                }
            ) from None