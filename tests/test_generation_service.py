import asyncio

from backend.app.core.exceptions import GenerationError
from backend.app.generation import GroundedAnswerService
from backend.app.retrieval import (
    RetrievalResult,
    RetrievedChunk,
)


class FakeLLMProvider:
    def __init__(self) -> None:
        self.call_count = 0
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        return (
            "Blood-pressure management includes reaching the "
            "recommended blood-pressure target [S1]. Lifestyle "
            "changes such as a healthy diet and physical activity "
            "are also recommended [S2]."
        )


class InvalidCitationLLMProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return "The recommendation is described in the source [S99]."


def build_retrieval_result() -> RetrievalResult:
    chunks = (
        RetrievedChunk(
            citation_id="S1",
            rank=1,
            content=(
                "Blood pressure should be managed toward the "
                "recommended systolic and diastolic targets."
            ),
            document_id="document-123",
            chunk_id="chunk-001",
            filename="guidelines.pdf",
            page_number=22,
            metadata={
                "document_id": "document-123",
                "chunk_id": "chunk-001",
            },
        ),
        RetrievedChunk(
            citation_id="S2",
            rank=2,
            content=(
                "Lifestyle counselling should include healthy diet, "
                "physical activity and tobacco cessation."
            ),
            document_id="document-123",
            chunk_id="chunk-002",
            filename="guidelines.pdf",
            page_number=23,
            metadata={
                "document_id": "document-123",
                "chunk_id": "chunk-002",
            },
        ),
    )

    context = (
        "[S1] | file=guidelines.pdf | page=22\n"
        f"{chunks[0].content}\n\n"
        "[S2] | file=guidelines.pdf | page=23\n"
        f"{chunks[1].content}"
    )

    return RetrievalResult(
        query=(
            "What treatment is recommended "
            "for high blood pressure?"
        ),
        chunks=chunks,
        context=context,
    )


async def main() -> None:
    llm_provider = FakeLLMProvider()

    service = GroundedAnswerService(
        llm_provider=llm_provider,
    )

    result = await service.generate(
        retrieval_result=build_retrieval_result(),
    )

    assert result.grounded is True
    assert result.has_citations is True
    assert result.citations == ("S1", "S2")
    assert len(result.sources) == 2
    assert result.sources[0].citation_id == "S1"
    assert result.sources[1].citation_id == "S2"
    assert llm_provider.call_count == 1
    assert "[S1]" in result.answer
    assert "[S2]" in result.answer

    empty_retrieval_result = RetrievalResult(
        query="What is the recommendation?",
        chunks=(),
        context="",
    )

    empty_result = await service.generate(
        retrieval_result=empty_retrieval_result,
    )

    assert empty_result.grounded is False
    assert empty_result.citations == ()
    assert empty_result.sources == ()
    assert llm_provider.call_count == 1

    invalid_service = GroundedAnswerService(
        llm_provider=InvalidCitationLLMProvider(),
    )

    invalid_citation_detected = False

    try:
        await invalid_service.generate(
            retrieval_result=build_retrieval_result(),
        )
    except GenerationError:
        invalid_citation_detected = True

    assert invalid_citation_detected is True

    print("\n=== GROUNDED GENERATION SERVICE TEST ===")
    print("Answer:", result.answer)
    print("Citations:", result.citations)
    print("Used sources:", len(result.sources))
    print("No-context protection confirmed.")
    print("Invalid-citation protection confirmed.")
    print(
        "Grounded generation service test "
        "passed successfully."
    )


if __name__ == "__main__":
    asyncio.run(main())

# uv run python -m tests.test_generation_service