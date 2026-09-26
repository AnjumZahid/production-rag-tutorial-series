import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from langchain_core.documents import Document

from backend.app.core.exceptions import (
    AppError,
    InvalidQueryError,
    RetrievalError,
)
from backend.app.core.logging import get_logger


logger = get_logger(__name__)


class VectorStoreProtocol(Protocol):
    """Vector-store operations required by the retrieval service."""

    def similarity_search(
        self,
        query: str,
        *,
        k: int | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        """Return documents semantically relevant to the query."""


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    """One normalized chunk returned by semantic retrieval."""

    citation_id: str
    rank: int
    content: str
    document_id: str | None
    chunk_id: str | None
    filename: str | None
    page_number: int | None
    metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Complete retrieval output for one user query."""

    query: str
    chunks: tuple[RetrievedChunk, ...]
    context: str

    @property
    def has_context(self) -> bool:
        """Return whether at least one useful chunk was retrieved."""

        return bool(self.chunks and self.context)


class RetrievalService:
    """
    Retrieves user-isolated document chunks and prepares LLM context.

    User and knowledge-base isolation are enforced by the scoped
    ChromaVectorStore instance supplied to this service.
    """

    def __init__(
        self,
        *,
        vector_store: VectorStoreProtocol,
        default_k: int = 4,
        max_k: int = 20,
        max_query_characters: int = 4000,
    ) -> None:
        if default_k < 1:
            raise ValueError("default_k must be at least 1.")

        if max_k < default_k:
            raise ValueError(
                "max_k must be greater than or equal to default_k."
            )

        if max_query_characters < 1:
            raise ValueError(
                "max_query_characters must be at least 1."
            )

        self.vector_store = vector_store
        self.default_k = default_k
        self.max_k = max_k
        self.max_query_characters = max_query_characters

    async def retrieve(
        self,
        *,
        query: str,
        k: int | None = None,
        document_id: str | None = None,
    ) -> RetrievalResult:
        """Retrieve relevant chunks and build citation-ready context."""

        normalized_query = self._normalize_query(query)
        effective_k = self._validate_k(k)

        try:
            documents = await asyncio.to_thread(
                self.vector_store.similarity_search,
                normalized_query,
                k=effective_k,
                document_id=document_id,
            )
        except AppError:
            raise
        except Exception as exc:
            logger.exception(
                "document_retrieval_failed",
                query_length=len(normalized_query),
                requested_results=effective_k,
                document_id=document_id,
                error_type=type(exc).__name__,
            )

            raise RetrievalError(
                details={
                    "document_id": document_id,
                    "requested_results": effective_k,
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            ) from exc

        chunks = tuple(
            self._normalize_document(
                document=document,
                rank=index,
            )
            for index, document in enumerate(
                documents,
                start=1,
            )
        )

        context = self._build_context(chunks)

        logger.info(
            "document_retrieval_completed",
            query_length=len(normalized_query),
            requested_results=effective_k,
            result_count=len(chunks),
            document_id=document_id,
        )

        return RetrievalResult(
            query=normalized_query,
            chunks=chunks,
            context=context,
        )

    def _normalize_query(self, query: str) -> str:
        """Validate and normalize a user retrieval query."""

        if not isinstance(query, str):
            raise InvalidQueryError(
                message="The query must be a string."
            )

        normalized_query = " ".join(query.split())

        if not normalized_query:
            raise InvalidQueryError(
                message="The query cannot be empty."
            )

        if len(normalized_query) > self.max_query_characters:
            raise InvalidQueryError(
                message=(
                    "The query exceeds the maximum permitted length."
                ),
                details={
                    "maximum_characters": self.max_query_characters,
                    "received_characters": len(normalized_query),
                },
            )

        return normalized_query

    def _validate_k(self, k: int | None) -> int:
        """Validate the requested number of retrieval results."""

        effective_k = self.default_k if k is None else k

        if not isinstance(effective_k, int):
            raise InvalidQueryError(
                message="The retrieval result count must be an integer."
            )

        if effective_k < 1 or effective_k > self.max_k:
            raise InvalidQueryError(
                message=(
                    f"The retrieval result count must be between "
                    f"1 and {self.max_k}."
                ),
                details={
                    "requested_results": effective_k,
                    "maximum_results": self.max_k,
                },
            )

        return effective_k

    def _normalize_document(
        self,
        *,
        document: Document,
        rank: int,
    ) -> RetrievedChunk:
        """Convert a LangChain document into a stable retrieval object."""

        metadata = dict(document.metadata or {})
        content = " ".join(document.page_content.split())

        filename = metadata.get("filename")

        if not filename:
            source = metadata.get("source")

            if source:
                filename = Path(str(source)).name

        raw_page_number = metadata.get(
            "page_number",
            metadata.get("page"),
        )

        page_number = self._safe_integer(raw_page_number)
        document_id = metadata.get("document_id")
        chunk_id = metadata.get("chunk_id")

        return RetrievedChunk(
            citation_id=f"S{rank}",
            rank=rank,
            content=content,
            document_id=(
                str(document_id)
                if document_id is not None
                else None
            ),
            chunk_id=(
                str(chunk_id)
                if chunk_id is not None
                else None
            ),
            filename=(
                str(filename)
                if filename is not None
                else None
            ),
            page_number=page_number,
            metadata=metadata,
        )

    @staticmethod
    def _safe_integer(value: Any) -> int | None:
        """Convert metadata to an integer when possible."""

        if value is None:
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _build_context(
        chunks: tuple[RetrievedChunk, ...],
    ) -> str:
        """Build numbered source blocks for the future LLM prompt."""

        context_blocks: list[str] = []

        for chunk in chunks:
            header_parts = [
                f"[{chunk.citation_id}]",
            ]

            if chunk.filename:
                header_parts.append(
                    f"file={chunk.filename}"
                )

            if chunk.page_number is not None:
                header_parts.append(
                    f"page={chunk.page_number}"
                )

            if chunk.document_id:
                header_parts.append(
                    f"document_id={chunk.document_id}"
                )

            header = " | ".join(header_parts)

            context_blocks.append(
                f"{header}\n{chunk.content}"
            )

        return "\n\n".join(context_blocks)