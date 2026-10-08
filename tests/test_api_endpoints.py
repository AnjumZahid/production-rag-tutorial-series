from fastapi.testclient import TestClient

import backend.app.api.routes as routes_module
from backend.app.api.app import create_app
from backend.app.api.dependencies import (
    get_database_session_dependency,
    get_embedding_provider_dependency,
    get_llm_provider_dependency,
)
from backend.app.retrieval import RetrievedChunk


class FakeSession:
    pass


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"


class FakeLLMProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return "A healthy diet is recommended [S1]."


class FakeVectorStore:
    def similarity_search(
        self,
        query: str,
        *,
        k: int | None = None,
        document_id: str | None = None,
    ):
        return []


class FakeRepository:
    def __init__(self, session) -> None:
        self.session = session


class FakeIngestionResult:
    document_id = "document-123"
    status = "completed"
    total_pages = 85
    chunk_count = 319
    vector_ids = tuple(
        f"vector-{index}"
        for index in range(1, 320)
    )


class FakeDocumentIngestionService:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    async def ingest_pdf(
        self,
        *,
        file_path,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
    ) -> FakeIngestionResult:
        return FakeIngestionResult()


class FakeRAGResult:
    query = "What lifestyle interventions are recommended?"
    answer = "A healthy diet is recommended [S1]."
    grounded = True
    citations = ("S1",)
    retrieved_chunk_count = 1
    sources = (
        RetrievedChunk(
            citation_id="S1",
            rank=1,
            content="A healthy diet is recommended.",
            document_id="document-123",
            chunk_id="chunk-1",
            filename="guidelines.pdf",
            page_number=10,
            metadata={},
        ),
    )


class FakeRAGQueryService:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    async def answer(
        self,
        *,
        query: str,
        k: int | None = None,
        document_id: str | None = None,
    ) -> FakeRAGResult:
        result = FakeRAGResult()
        result.query = query
        return result


async def override_database_session():
    yield FakeSession()


def override_embedding_provider():
    return FakeEmbeddingProvider()


def override_llm_provider():
    return FakeLLMProvider()


def fake_get_vector_store(**kwargs):
    return FakeVectorStore()


def main() -> None:
    routes_module.DocumentRepository = FakeRepository
    routes_module.DocumentIngestionService = (
        FakeDocumentIngestionService
    )
    routes_module.RAGQueryService = FakeRAGQueryService
    routes_module.get_vector_store = fake_get_vector_store

    app = create_app()

    app.dependency_overrides[
        get_database_session_dependency
    ] = override_database_session

    app.dependency_overrides[
        get_embedding_provider_dependency
    ] = override_embedding_provider

    app.dependency_overrides[
        get_llm_provider_dependency
    ] = override_llm_provider

    client = TestClient(app)

    headers = {
        "X-Organization-ID": "test-org",
        "X-User-ID": "test-user",
    }

    health_response = client.get("/api/v1/health")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "healthy"

    upload_response = client.post(
        "/api/v1/documents",
        headers=headers,
        data={
            "knowledge_base_id": "test-kb",
        },
        files={
            "file": (
                "guidelines.pdf",
                b"%PDF-1.4 fake pdf content",
                "application/pdf",
            )
        },
    )

    assert upload_response.status_code == 200
    upload_json = upload_response.json()
    assert upload_json["document_id"] == "document-123"
    assert upload_json["status"] == "completed"
    assert upload_json["chunk_count"] == 319
    assert upload_json["vector_count"] == 319

    invalid_upload_response = client.post(
        "/api/v1/documents",
        headers=headers,
        data={
            "knowledge_base_id": "test-kb",
        },
        files={
            "file": (
                "notes.txt",
                b"not a pdf",
                "text/plain",
            )
        },
    )

    assert invalid_upload_response.status_code == 400
    assert (
        invalid_upload_response.json()["error"]["code"]
        == "INVALID_UPLOAD"
    )

    query_response = client.post(
        "/api/v1/rag/query",
        headers=headers,
        json={
            "knowledge_base_id": "test-kb",
            "query": (
                "What lifestyle interventions are recommended?"
            ),
            "k": 5,
            "document_id": "document-123",
        },
    )

    assert query_response.status_code == 200
    query_json = query_response.json()
    assert query_json["grounded"] is True
    assert query_json["citations"] == ["S1"]
    assert query_json["sources"][0]["citation_id"] == "S1"
    assert query_json["retrieved_chunk_count"] == 1

    print("\n=== FASTAPI ENDPOINT TEST ===")
    print("Health endpoint confirmed.")
    print("Document upload endpoint confirmed.")
    print("Invalid non-PDF rejection confirmed.")
    print("RAG query endpoint confirmed.")
    print("FastAPI endpoint test passed successfully.")


if __name__ == "__main__":
    main()

# uv run python -m tests.test_api_endpoints