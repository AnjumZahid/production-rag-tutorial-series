from dataclasses import dataclass

from backend.app.core.logging import get_logger
from backend.app.generation import GroundedAnswerService
from backend.app.retrieval import (
    RetrievalService,
    RetrievedChunk,
)


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RAGQueryResult:
    """Final output of one retrieval-grounded question."""

    query: str
    answer: str
    grounded: bool
    citations: tuple[str, ...]
    sources: tuple[RetrievedChunk, ...]
    retrieved_chunk_count: int

    @property
    def has_sources(self) -> bool:
        """Return whether the final answer used any sources."""

        return bool(self.sources)


class RAGQueryService:
    """
    Orchestrates retrieval and grounded answer generation.

    The service:
    1. Retrieves relevant chunks from the scoped vector store.
    2. Sends the prepared context to the grounded generation service.
    3. Returns the final answer and validated source objects.
    """

    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        generation_service: GroundedAnswerService,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.generation_service = generation_service

    async def answer(
        self,
        *,
        query: str,
        k: int | None = None,
        document_id: str | None = None,
    ) -> RAGQueryResult:
        """Answer one question using indexed document evidence."""

        retrieval_result = await self.retrieval_service.retrieve(
            query=query,
            k=k,
            document_id=document_id,
        )

        generated_answer = await self.generation_service.generate(
            retrieval_result=retrieval_result,
        )

        logger.info(
            "rag_query_completed",
            query_length=len(retrieval_result.query),
            retrieved_chunk_count=len(
                retrieval_result.chunks
            ),
            used_source_count=len(
                generated_answer.sources
            ),
            citation_count=len(
                generated_answer.citations
            ),
            grounded=generated_answer.grounded,
            document_id=document_id,
        )

        return RAGQueryResult(
            query=retrieval_result.query,
            answer=generated_answer.answer,
            grounded=generated_answer.grounded,
            citations=generated_answer.citations,
            sources=generated_answer.sources,
            retrieved_chunk_count=len(
                retrieval_result.chunks
            ),
        )