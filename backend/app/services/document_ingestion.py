import asyncio
from collections.abc import Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from langchain_core.documents import Document
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import (
    AppError,
    DocumentIngestionError,
    DuplicateDocumentError,
)
from backend.app.core.logging import get_logger
from backend.app.database.enums import DocumentStatus
from backend.app.database.repositories import (
    ChunkReference,
    DocumentRepository,
)


logger = get_logger(__name__)


class DocumentLoaderProtocol(Protocol):
    def load(self, path: Path) -> list[Document]:
        """Load a document source."""


class DocumentParserProtocol(Protocol):
    def parse(
        self,
        documents: Sequence[Document],
    ) -> list[Document]:
        """Parse loaded documents."""


class TextCleanerProtocol(Protocol):
    def clean(
        self,
        documents: Sequence[Document],
    ) -> list[Document]:
        """Clean parsed documents."""


class DocumentChunkerProtocol(Protocol):
    def split(
        self,
        documents: Sequence[Document],
    ) -> list[Document]:
        """Split cleaned documents into chunks."""


class EmbeddingProviderProtocol(Protocol):
    def embed_documents(
        self,
        texts: Sequence[str],
    ) -> list[list[float]]:
        """Generate document embeddings."""


class VectorStoreProtocol(Protocol):
    def add_documents(
        self,
        documents: Sequence[Document],
        embeddings: Sequence[Sequence[float]],
    ) -> list[str]:
        """Store documents and return their vector IDs."""

    def delete_documents(
        self,
        vector_ids: Sequence[str],
    ) -> None:
        """Delete vectors by their IDs."""


@dataclass(frozen=True, slots=True)
class DocumentIngestionResult:
    """Successful document-ingestion result."""

    document_id: str
    status: str
    total_pages: int
    chunk_count: int
    vector_ids: tuple[str, ...]


class DocumentIngestionService:
    """
    Coordinates the complete offline document-indexing workflow.

    The individual components remain independent. This service controls:
    - duplicate checking
    - MySQL status changes
    - document processing
    - embedding generation
    - vector storage
    - MySQL chunk references
    - failure cleanup
    """

    def __init__(
        self,
        *,
        session: AsyncSession,
        repository: DocumentRepository,
        loader: DocumentLoaderProtocol,
        parser: DocumentParserProtocol,
        cleaner: TextCleanerProtocol,
        chunker: DocumentChunkerProtocol,
        embedding_provider: EmbeddingProviderProtocol,
        vector_store: VectorStoreProtocol,
        embedding_provider_name: str,
        embedding_model_name: str,
        vector_store_provider_name: str,
    ) -> None:
        self.session = session
        self.repository = repository
        self.loader = loader
        self.parser = parser
        self.cleaner = cleaner
        self.chunker = chunker
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.embedding_provider_name = embedding_provider_name
        self.embedding_model_name = embedding_model_name
        self.vector_store_provider_name = vector_store_provider_name

    async def ingest_pdf(
        self,
        *,
        file_path: str | Path,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
    ) -> DocumentIngestionResult:
        """
        Process one PDF and register it in MySQL and the vector store.
        """

        resolved_path = Path(file_path).resolve()

        self._validate_pdf_path(resolved_path)

        file_hash = await asyncio.to_thread(
            self._calculate_file_hash,
            resolved_path,
        )

        existing_document = await self.repository.get_by_hash(
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            file_hash=file_hash,
        )

        if existing_document is not None:
            raise DuplicateDocumentError(
                details={
                    "document_id": existing_document.id,
                    "filename": existing_document.filename,
                    "status": existing_document.status,
                }
            )

        document_id: str | None = None
        stored_vector_ids: list[str] = []

        try:
            document_record = await self.repository.create_document(
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                filename=resolved_path.name,
                file_hash=file_hash,
                file_size_bytes=resolved_path.stat().st_size,
            )

            document_id = document_record.id

            # Preserve the pending record even if later processing fails.
            await self.session.commit()

            await self.repository.update_status(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                status=DocumentStatus.PROCESSING,
            )
            await self.session.commit()

            loaded_documents = await asyncio.to_thread(
                self.loader.load,
                resolved_path,
            )

            if not loaded_documents:
                raise DocumentIngestionError(
                    message="The PDF loader returned no pages.",
                    details={
                        "filename": resolved_path.name,
                    },
                )

            parsed_documents = await asyncio.to_thread(
                self.parser.parse,
                loaded_documents,
            )

            cleaned_documents = await asyncio.to_thread(
                self.cleaner.clean,
                parsed_documents,
            )

            chunks = await asyncio.to_thread(
                self.chunker.split,
                cleaned_documents,
            )

            if not chunks:
                raise DocumentIngestionError(
                    message="No chunks were created from the document.",
                    details={
                        "document_id": document_id,
                    },
                )

            self._add_ownership_metadata(
                chunks=chunks,
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                file_hash=file_hash,
                filename=resolved_path.name,
            )

            chunk_texts = [
                chunk.page_content
                for chunk in chunks
            ]

            embeddings = await asyncio.to_thread(
                self.embedding_provider.embed_documents,
                chunk_texts,
            )

            self._validate_embeddings(
                chunks=chunks,
                embeddings=embeddings,
                document_id=document_id,
            )

            stored_vector_ids = await asyncio.to_thread(
                self.vector_store.add_documents,
                chunks,
                embeddings,
            )

            if len(stored_vector_ids) != len(chunks):
                raise DocumentIngestionError(
                    message=(
                        "The vector store returned an unexpected "
                        "number of vector IDs."
                    ),
                    details={
                        "document_id": document_id,
                        "chunk_count": len(chunks),
                        "vector_id_count": len(stored_vector_ids),
                    },
                )

            chunk_references = self._build_chunk_references(
                chunks=chunks,
                vector_ids=stored_vector_ids,
            )

            await self.repository.add_chunk_references(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                chunk_references=chunk_references,
            )

            embedding_dimension = len(embeddings[0])

            completed_document = await self.repository.update_status(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                status=DocumentStatus.COMPLETED,
                embedding_provider=self.embedding_provider_name,
                embedding_model=self.embedding_model_name,
                embedding_dimension=embedding_dimension,
                vector_store_provider=self.vector_store_provider_name,
                total_pages=len(loaded_documents),
                error_message=None,
            )

            await self.session.commit()

            logger.info(
                "document_ingestion_completed",
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                page_count=len(loaded_documents),
                chunk_count=len(chunks),
            )

            return DocumentIngestionResult(
                document_id=document_id,
                status=completed_document.status,
                total_pages=len(loaded_documents),
                chunk_count=len(chunks),
                vector_ids=tuple(stored_vector_ids),
            )

        except Exception as exc:
            await self.session.rollback()

            if stored_vector_ids:
                try:
                    await asyncio.to_thread(
                        self.vector_store.delete_documents,
                        stored_vector_ids,
                    )
                except Exception as cleanup_exc:
                    logger.exception(
                        "document_vector_cleanup_failed",
                        document_id=document_id,
                        error_type=type(cleanup_exc).__name__,
                    )

            if document_id is not None:
                await self._mark_document_failed(
                    document_id=document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                    error_message=str(exc),
                )

            logger.exception(
                "document_ingestion_failed",
                document_id=document_id,
                filename=resolved_path.name,
                error_type=type(exc).__name__,
            )

            if isinstance(exc, AppError):
                raise

            raise DocumentIngestionError(
                details={
                    "document_id": document_id,
                    "filename": resolved_path.name,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            ) from exc

    async def _mark_document_failed(
        self,
        *,
        document_id: str,
        organization_id: str,
        user_id: str,
        error_message: str,
    ) -> None:
        """Persist a failed status after rolling back current work."""

        try:
            await self.repository.update_status(
                document_id=document_id,
                organization_id=organization_id,
                user_id=user_id,
                status=DocumentStatus.FAILED,
                error_message=error_message[:2000],
            )
            await self.session.commit()
        except Exception as status_exc:
            await self.session.rollback()

            logger.exception(
                "document_failed_status_update_failed",
                document_id=document_id,
                error_type=type(status_exc).__name__,
            )

    @staticmethod
    def _validate_pdf_path(file_path: Path) -> None:
        if not file_path.exists():
            raise DocumentIngestionError(
                message="The PDF file does not exist.",
                details={
                    "file_path": str(file_path),
                },
            )

        if not file_path.is_file():
            raise DocumentIngestionError(
                message="The supplied path is not a file.",
                details={
                    "file_path": str(file_path),
                },
            )

        if file_path.suffix.lower() != ".pdf":
            raise DocumentIngestionError(
                message="Only PDF files are supported in this ingestion step.",
                details={
                    "file_path": str(file_path),
                },
            )

    @staticmethod
    def _calculate_file_hash(file_path: Path) -> str:
        hasher = sha256()

        with file_path.open("rb") as file:
            while data := file.read(1024 * 1024):
                hasher.update(data)

        return hasher.hexdigest()

    @staticmethod
    def _add_ownership_metadata(
        *,
        chunks: Sequence[Document],
        document_id: str,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
        file_hash: str,
        filename: str,
    ) -> None:
        """
        Add mandatory ownership and document metadata to every chunk.

        Existing source, page and chunk metadata are preserved.
        """

        for chunk in chunks:
            chunk.metadata.update(
                {
                    "document_id": document_id,
                    "organization_id": organization_id,
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "file_hash": file_hash,
                    "filename": filename,
                }
            )

    @staticmethod
    def _validate_embeddings(
        *,
        chunks: Sequence[Document],
        embeddings: Sequence[Sequence[float]],
        document_id: str,
    ) -> None:
        if len(embeddings) != len(chunks):
            raise DocumentIngestionError(
                message=(
                    "The embedding provider returned an unexpected "
                    "number of embeddings."
                ),
                details={
                    "document_id": document_id,
                    "chunk_count": len(chunks),
                    "embedding_count": len(embeddings),
                },
            )

        if not embeddings or not embeddings[0]:
            raise DocumentIngestionError(
                message="The embedding provider returned empty embeddings.",
                details={
                    "document_id": document_id,
                },
            )

        expected_dimension = len(embeddings[0])

        if any(
            len(embedding) != expected_dimension
            for embedding in embeddings
        ):
            raise DocumentIngestionError(
                message="Embedding dimensions are inconsistent.",
                details={
                    "document_id": document_id,
                },
            )

    @staticmethod
    def _build_chunk_references(
        *,
        chunks: Sequence[Document],
        vector_ids: Sequence[str],
    ) -> list[ChunkReference]:
        references: list[ChunkReference] = []

        for chunk, vector_id in zip(
            chunks,
            vector_ids,
            strict=True,
        ):
            chunk_id = chunk.metadata.get("chunk_id")

            if not chunk_id:
                raise DocumentIngestionError(
                    message="A chunk is missing its chunk_id metadata."
                )

            page_number = chunk.metadata.get(
                "page_number",
                chunk.metadata.get("page", 0),
            )

            chunk_index = chunk.metadata.get(
                "chunk_index",
                0,
            )

            references.append(
                ChunkReference(
                    chunk_id=str(chunk_id),
                    vector_id=str(vector_id),
                    page_number=int(page_number),
                    chunk_index=int(chunk_index),
                )
            )

        return references