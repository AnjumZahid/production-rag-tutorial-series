from types import SimpleNamespace

from fastapi.testclient import TestClient

import backend.app.api.routes as routes_module
from backend.app.api.app import create_app
from backend.app.api.dependencies import (
    get_database_session_dependency,
    get_embedding_provider_dependency,
    get_llm_provider_dependency,
)
from backend.app.auth import create_access_token
from backend.app.retrieval import RetrievedChunk


class FakeDatabaseResult:
    """
    Minimal SQLAlchemy-result replacement.

    Step 33B organization authorization checks the database
    for an active membership before allowing protected routes.
    This fake result returns an active owner membership for the
    authenticated test user.
    """

    def scalar_one_or_none(self):
        return SimpleNamespace(
            id="membership-123",
            organization_id="test-org",
            user_id="test-user",
            role="owner",
            is_active=True,
        )


class FakeSession:
    """
    Minimal async database-session replacement.

    The real Step 33B organization-access dependency calls
    session.execute(), so the fake session must support it.
    """

    async def execute(
        self,
        *args,
        **kwargs,
    ) -> FakeDatabaseResult:
        return FakeDatabaseResult()


class FakeEmbeddingProvider:
    model_name = "fake-embedding-model"


class FakeLLMProvider:
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return (
            "A healthy diet and physical activity "
            "are recommended [S1]."
        )


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
        assert organization_id == "test-org"
        assert user_id == "test-user"
        assert knowledge_base_id == "test-kb"

        return FakeIngestionResult()


class FakeRAGResult:
    query = (
        "What lifestyle interventions "
        "are recommended?"
    )

    answer = (
        "A healthy diet and physical activity "
        "are recommended [S1]."
    )

    grounded = True
    citations = ("S1",)
    retrieved_chunk_count = 1

    sources = (
        RetrievedChunk(
            citation_id="S1",
            rank=1,
            content=(
                "A healthy diet is recommended."
            ),
            document_id="document-123",
            chunk_id="chunk-1",
            filename="guidelines.pdf",
            page_number=10,
            metadata={},
        ),
    )


class FakeRAGQueryService:
    def __init__(
        self,
        **kwargs,
    ) -> None:
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


def fake_get_vector_store(
    **kwargs,
):
    assert (
        kwargs["organization_id"]
        == "test-org"
    )

    assert (
        kwargs["user_id"]
        == "test-user"
    )

    assert (
        kwargs["knowledge_base_id"]
        == "test-kb"
    )

    return FakeVectorStore()


def main() -> None:
    # --------------------------------------------------
    # Replace real document/RAG services with test fakes
    # --------------------------------------------------

    routes_module.DocumentRepository = (
        FakeRepository
    )

    routes_module.DocumentIngestionService = (
        FakeDocumentIngestionService
    )

    routes_module.RAGQueryService = (
        FakeRAGQueryService
    )

    routes_module.get_vector_store = (
        fake_get_vector_store
    )

    # --------------------------------------------------
    # Create FastAPI app
    # --------------------------------------------------

    app = create_app()

    # --------------------------------------------------
    # Override external/database dependencies
    # --------------------------------------------------

    app.dependency_overrides[
        get_database_session_dependency
    ] = override_database_session

    app.dependency_overrides[
        get_embedding_provider_dependency
    ] = override_embedding_provider

    app.dependency_overrides[
        get_llm_provider_dependency
    ] = override_llm_provider

    # --------------------------------------------------
    # Important Step 33B behavior
    #
    # We intentionally DO NOT override:
    #
    # get_request_identity
    # get_organization_access
    # require_document_write_access
    # require_document_read_access
    #
    # This keeps the real JWT + membership + role
    # authorization flow active in this endpoint test.
    # --------------------------------------------------

    token = create_access_token(
        user_id="test-user",
        organization_id="test-org",
        expires_minutes=60,
    )

    auth_headers = {
        "Authorization": (
            f"Bearer {token}"
        ),
    }

    # --------------------------------------------------
    # Run endpoint tests
    # --------------------------------------------------

    with TestClient(app) as client:

        # ----------------------------------------------
        # 1. Health endpoint
        # ----------------------------------------------

        health_response = client.get(
            "/api/v1/health"
        )

        assert (
            health_response.status_code
            == 200
        )

        health_json = (
            health_response.json()
        )

        assert (
            health_json["status"]
            == "healthy"
        )

        # ----------------------------------------------
        # 2. Missing JWT must fail
        # ----------------------------------------------

        missing_token_response = (
            client.post(
                "/api/v1/rag/query",
                json={
                    "knowledge_base_id": (
                        "test-kb"
                    ),
                    "query": (
                        "What is recommended?"
                    ),
                    "k": 5,
                },
            )
        )

        assert (
            missing_token_response.status_code
            == 401
        )

        assert (
            missing_token_response.headers.get(
                "www-authenticate"
            )
            == "Bearer"
        )

        # ----------------------------------------------
        # 3. Invalid JWT must fail
        # ----------------------------------------------

        invalid_token_response = (
            client.post(
                "/api/v1/rag/query",
                headers={
                    "Authorization": (
                        "Bearer invalid-token"
                    )
                },
                json={
                    "knowledge_base_id": (
                        "test-kb"
                    ),
                    "query": (
                        "What is recommended?"
                    ),
                    "k": 5,
                },
            )
        )

        assert (
            invalid_token_response.status_code
            == 401
        )

        # ----------------------------------------------
        # 4. Owner can upload document
        # ----------------------------------------------

        upload_response = client.post(
            "/api/v1/documents",
            headers=auth_headers,
            data={
                "knowledge_base_id": (
                    "test-kb"
                ),
            },
            files={
                "file": (
                    "guidelines.pdf",
                    b"%PDF-1.4 fake pdf content",
                    "application/pdf",
                )
            },
        )

        assert (
            upload_response.status_code
            == 201
        )

        upload_json = (
            upload_response.json()
        )

        assert (
            upload_json["document_id"]
            == "document-123"
        )

        assert (
            upload_json["status"]
            == "completed"
        )

        assert (
            upload_json["filename"]
            == "guidelines.pdf"
        )

        assert (
            upload_json["chunk_count"]
            == 319
        )

        assert (
            upload_json["vector_count"]
            == 319
        )

        # ----------------------------------------------
        # 5. Owner can query RAG
        # ----------------------------------------------

        query_response = client.post(
            "/api/v1/rag/query",
            headers=auth_headers,
            json={
                "knowledge_base_id": (
                    "test-kb"
                ),
                "query": (
                    "What lifestyle interventions "
                    "are recommended?"
                ),
                "k": 5,
                "document_id": (
                    "document-123"
                ),
            },
        )

        assert (
            query_response.status_code
            == 200
        )

        query_json = (
            query_response.json()
        )

        assert (
            query_json["grounded"]
            is True
        )

        assert (
            query_json["citations"]
            == ["S1"]
        )

        assert (
            query_json[
                "sources"
            ][0]["citation_id"]
            == "S1"
        )

        assert (
            query_json[
                "retrieved_chunk_count"
            ]
            == 1
        )

        # ----------------------------------------------
        # 6. Invalid PDF protection
        # ----------------------------------------------

        invalid_upload_response = (
            client.post(
                "/api/v1/documents",
                headers=auth_headers,
                data={
                    "knowledge_base_id": (
                        "test-kb"
                    ),
                },
                files={
                    "file": (
                        "notes.txt",
                        b"not a pdf",
                        "text/plain",
                    )
                },
            )
        )

        assert (
            invalid_upload_response.status_code
            == 400
        )

        assert (
            invalid_upload_response
            .json()["error"]["code"]
            == "INVALID_UPLOAD"
        )

    # --------------------------------------------------
    # Test summary
    # --------------------------------------------------

    print(
        "\n=== FASTAPI ENDPOINT TEST ==="
    )

    print(
        "Health:",
        health_json,
    )

    print(
        "Missing-token protection confirmed."
    )

    print(
        "Invalid-token protection confirmed."
    )

    print(
        "Active owner membership "
        "authorization confirmed."
    )

    print(
        "Upload document:",
        upload_json["document_id"],
    )

    print(
        "RAG answer:",
        query_json["answer"],
    )

    print(
        "Invalid PDF protection confirmed."
    )

    print(
        "FastAPI endpoint test "
        "passed successfully."
    )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_api_endpoints