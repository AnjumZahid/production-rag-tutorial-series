
from langchain_core.documents import Document

from backend.app.embeddings.factory import get_embedding_provider
from backend.app.vectorstores.chroma_store import ChromaVectorStore


def main() -> None:
    embedding_provider = get_embedding_provider()

    vector_store = ChromaVectorStore(
        embedding_provider=embedding_provider,
        organization_id="organization-test-001",
        user_id="user-test-001",
        knowledge_base_id="medical-kb-001",
        persist_directory="./data/chroma_test",
    )

    documents = [
        Document(
            page_content=(
                "High blood pressure can damage the heart "
                "and increase the risk of stroke."
            ),
            metadata={
                "chunk_id": "medical-chunk-001",
                "document_id": "medical-document-001",
                "filename": "medical.pdf",
                "page_number": 1,
            },
        ),
        Document(
            page_content=(
                "Regular exercise can improve cardiovascular health."
            ),
            metadata={
                "chunk_id": "medical-chunk-002",
                "document_id": "medical-document-001",
                "filename": "medical.pdf",
                "page_number": 2,
            },
        ),
    ]

    stored_ids = vector_store.add_documents(documents)

    results = vector_store.similarity_search(
        query="How does blood pressure affect the heart?",
        k=2,
    )

    print("\n=== ORGANIZATION CHROMA TEST ===")
    print("Tenant:", vector_store.tenant_name)
    print("Database:", vector_store.database_name)
    print("Collection:", vector_store.collection_name)
    print("Stored IDs:", stored_ids)
    print("Results:", len(results))

    for index, result in enumerate(results, start=1):
        print(f"\nResult {index}:")
        print("Text:", result.page_content)
        print("Metadata:", result.metadata)

        assert (
            result.metadata["organization_id"]
            == "organization-test-001"
        )

        assert (
            result.metadata["user_id"]
            == "user-test-001"
        )

        assert (
            result.metadata["knowledge_base_id"]
            == "medical-kb-001"
        )

    assert len(stored_ids) == 2

    vector_store.close()

    print("\nOrganization-isolated Chroma test passed.")


if __name__ == "__main__":
    main()

# uv run python -m tests.test_chroma_store