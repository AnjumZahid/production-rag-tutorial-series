import asyncio
import re
from dataclasses import dataclass
from typing import Protocol

from backend.app.core.exceptions import (
    AppError,
    GenerationError,
)
from backend.app.core.logging import get_logger
from backend.app.generation.prompts import (
    GROUNDING_SYSTEM_PROMPT,
    build_grounded_user_prompt,
)
from backend.app.retrieval import (
    RetrievalResult,
    RetrievedChunk,
)


logger = get_logger(__name__)

CITATION_GROUP_PATTERN = re.compile(
    r"\[\s*((?:S\d+\s*,\s*)*S\d+)\s*\]"
)

CITATION_ID_PATTERN = re.compile(r"S\d+")


class LLMProviderProtocol(Protocol):
    """Language-model operation required by the generation service."""

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text response."""


@dataclass(frozen=True, slots=True)
class GroundedAnswer:
    """Final answer and its validated source information."""

    query: str
    answer: str
    citations: tuple[str, ...]
    sources: tuple[RetrievedChunk, ...]
    grounded: bool

    @property
    def has_citations(self) -> bool:
        """Return whether the answer contains validated citations."""

        return bool(self.citations)


class GroundedAnswerService:
    """
    Generates an answer using only the retrieved document context.

    Responsibilities:
    - select context within a safe size limit
    - build the grounded prompt
    - call the configured LLM provider
    - validate model citations
    - return only the sources used by the answer
    """

    def __init__(
        self,
        *,
        llm_provider: LLMProviderProtocol,
        max_context_characters: int = 24_000,
    ) -> None:
        if max_context_characters < 1:
            raise ValueError(
                "max_context_characters must be at least 1."
            )

        self.llm_provider = llm_provider
        self.max_context_characters = max_context_characters

    async def generate(
        self,
        *,
        retrieval_result: RetrievalResult,
    ) -> GroundedAnswer:
        """
        Generate and validate one citation-grounded answer.
        """

        if not retrieval_result.has_context:
            return GroundedAnswer(
                query=retrieval_result.query,
                answer=(
                    "I do not have enough information in the indexed "
                    "documents to answer this question."
                ),
                citations=(),
                sources=(),
                grounded=False,
            )

        selected_chunks = self._select_chunks(
            retrieval_result.chunks
        )

        if not selected_chunks:
            return GroundedAnswer(
                query=retrieval_result.query,
                answer=(
                    "I do not have enough information in the indexed "
                    "documents to answer this question."
                ),
                citations=(),
                sources=(),
                grounded=False,
            )

        context = self._build_context(selected_chunks)

        user_prompt = build_grounded_user_prompt(
            question=retrieval_result.query,
            context=context,
        )

        try:
            raw_answer = await asyncio.to_thread(
                self.llm_provider.generate,
                system_prompt=GROUNDING_SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        except AppError:
            raise
        except Exception as exc:
            logger.error(
                "grounded_answer_generation_failed",
                query_length=len(retrieval_result.query),
                source_count=len(selected_chunks),
                error_type=type(exc).__name__,
            )

            raise GenerationError(
                details={
                    "error_type": type(exc).__name__,
                    "source_count": len(selected_chunks),
                }
            ) from None

        answer = self._normalize_answer(raw_answer)

        citation_ids = self._extract_citations(answer)

        available_sources = {
            chunk.citation_id: chunk
            for chunk in selected_chunks
        }

        invalid_citations = [
            citation_id
            for citation_id in citation_ids
            if citation_id not in available_sources
        ]

        if invalid_citations:
            raise GenerationError(
                message=(
                    "The language model returned one or more "
                    "unsupported citations."
                ),
                details={
                    "invalid_citations": invalid_citations,
                    "available_citations": sorted(
                        available_sources.keys()
                    ),
                },
            )

        if not citation_ids:
            raise GenerationError(
                message=(
                    "The language model returned an answer "
                    "without source citations."
                ),
                details={
                    "available_citations": sorted(
                        available_sources.keys()
                    ),
                },
            )

        used_sources = tuple(
            available_sources[citation_id]
            for citation_id in citation_ids
        )

        logger.info(
            "grounded_answer_generation_completed",
            query_length=len(retrieval_result.query),
            available_source_count=len(selected_chunks),
            used_source_count=len(used_sources),
            citation_count=len(citation_ids),
        )

        return GroundedAnswer(
            query=retrieval_result.query,
            answer=answer,
            citations=tuple(citation_ids),
            sources=used_sources,
            grounded=True,
        )

    def _select_chunks(
        self,
        chunks: tuple[RetrievedChunk, ...],
    ) -> tuple[RetrievedChunk, ...]:
        """
        Select complete source chunks without exceeding the context limit.
        """

        selected: list[RetrievedChunk] = []
        used_characters = 0

        for chunk in chunks:
            block = self._format_chunk(chunk)
            block_length = len(block)

            if (
                selected
                and used_characters + block_length
                > self.max_context_characters
            ):
                break

            if (
                not selected
                and block_length > self.max_context_characters
            ):
                truncated_content = chunk.content[
                    : self.max_context_characters
                ]

                selected.append(
                    RetrievedChunk(
                        citation_id=chunk.citation_id,
                        rank=chunk.rank,
                        content=truncated_content,
                        document_id=chunk.document_id,
                        chunk_id=chunk.chunk_id,
                        filename=chunk.filename,
                        page_number=chunk.page_number,
                        metadata=chunk.metadata,
                    )
                )
                break

            selected.append(chunk)
            used_characters += block_length

        return tuple(selected)

    @staticmethod
    def _format_chunk(chunk: RetrievedChunk) -> str:
        """Format one source chunk for the language-model prompt."""

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

        return f"{header}\n{chunk.content}"

    def _build_context(
        self,
        chunks: tuple[RetrievedChunk, ...],
    ) -> str:
        """Build the final source context sent to the LLM."""

        return "\n\n".join(
            self._format_chunk(chunk)
            for chunk in chunks
        )

    @staticmethod
    def _normalize_answer(answer: str) -> str:
        """Validate and normalize the generated answer."""

        if not isinstance(answer, str):
            raise GenerationError(
                message=(
                    "The language model returned a non-text response."
                )
            )

        normalized_answer = answer.strip()

        if not normalized_answer:
            raise GenerationError(
                message=(
                    "The language model returned an empty response."
                )
            )

        return normalized_answer

    @staticmethod
    def _extract_citations(answer: str) -> list[str]:
        """
        Extract individual and grouped citation IDs.

        Supported examples:
        [S1]
        [S1, S2]
        [S1, S2, S3]
        """

        citations: list[str] = []
        seen: set[str] = set()

        for citation_group in CITATION_GROUP_PATTERN.findall(
            answer
        ):
            citation_ids = CITATION_ID_PATTERN.findall(
                citation_group
            )

            for citation_id in citation_ids:
                if citation_id in seen:
                    continue

                citations.append(citation_id)
                seen.add(citation_id)

        return citations