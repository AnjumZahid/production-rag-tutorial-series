import asyncio

from langchain_core.documents import Document

from backend.app.core.exceptions import InvalidQueryError
from backend.app.retrieval import RetrievalService


class FakeVectorStore:
    def __init__(self) -> None:
        self.last_query: str | None = None
        self.last_k: int | None = None
        self.last_document_id: str | None = None

    def similarity_search(
        self,
        query: str,
        *,
        k: int | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        self.last_query = query
        self.last_k = k
        self.last_document_id = document_id

        return [
            Document(
                page_content=(
                    "Blood pressure is controlled when systolic "
                    "pressure is below the recommended target."
                ),
                metadata={
                    "document_id": "document-123",
                    "chunk_id": "chunk-001",
                    "filename": "guidelines.pdf",
                    "page_number": 22,
                    "organization_id": "organization-1",
                    "user_id": "user-1",
                    "knowledge_base_id": "knowledge-base-1",
                },
            ),
            Document(
                page_content=(
                    "Lifestyle interventions include healthy diet, "
                    "physical activity and tobacco cessation."
                ),
                metadata={
                    "document_id": "document-123",
                    "chunk_id": "chunk-002",
                    "source": "docs/guidelines.pdf",
                    "page": 23,
                    "organization_id": "organization-1",
                    "user_id": "user-1",
                    "knowledge_base_id": "knowledge-base-1",
                },
            ),
        ]


async def main() -> None:
    vector_store = FakeVectorStore()

    service = RetrievalService(
        vector_store=vector_store,
        default_k=4,
        max_k=10,
    )

    result = await service.retrieve(
        query=(
            "  What treatment is recommended "
            "for high blood pressure?  "
        ),
        k=3,
        document_id="document-123",
    )

    assert result.query == (
        "What treatment is recommended "
        "for high blood pressure?"
    )

    assert result.has_context is True
    assert len(result.chunks) == 2

    assert result.chunks[0].citation_id == "S1"
    assert result.chunks[0].page_number == 22
    assert result.chunks[0].filename == "guidelines.pdf"

    assert result.chunks[1].citation_id == "S2"
    assert result.chunks[1].page_number == 23
    assert result.chunks[1].filename == "guidelines.pdf"

    assert "[S1]" in result.context
    assert "[S2]" in result.context
    assert "page=22" in result.context
    assert "page=23" in result.context

    assert vector_store.last_query == (
        "What treatment is recommended "
        "for high blood pressure?"
    )
    assert vector_store.last_k == 3
    assert (
        vector_store.last_document_id
        == "document-123"
    )

    invalid_query_detected = False

    try:
        await service.retrieve(
            query="   ",
        )
    except InvalidQueryError:
        invalid_query_detected = True

    assert invalid_query_detected is True

    print("\n=== RETRIEVAL SERVICE TEST ===")
    print("Normalized query:", result.query)
    print("Retrieved chunks:", len(result.chunks))
    print("First citation:", result.chunks[0].citation_id)
    print("Second citation:", result.chunks[1].citation_id)
    print("Invalid-query protection confirmed.")
    print("\nGenerated context:\n")
    print(result.context)
    print("\nRetrieval service test passed successfully.")


if __name__ == "__main__":
    asyncio.run(main())

# uv run python -m tests.test_retrieval_service