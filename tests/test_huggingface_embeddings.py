from backend.app.embeddings.huggingface import (
    HuggingFaceEmbeddingProvider,
)


def main() -> None:
    provider = HuggingFaceEmbeddingProvider()

    document_texts = [
        "High blood pressure can damage the heart.",
        "Regular exercise can improve cardiovascular health.",
    ]

    query = "How does blood pressure affect the heart?"

    document_vectors = provider.embed_documents(document_texts)
    query_vector = provider.embed_query(query)

    print("\n=== EMBEDDING PROVIDER TEST ===")
    print("Provider:", provider.provider_name)
    print("Model:", provider.model_name)
    print("Document vectors:", len(document_vectors))
    print("Document vector dimension:", len(document_vectors[0]))
    print("Query vector dimension:", len(query_vector))
    print("First five query values:", query_vector[:5])

    assert len(document_vectors) == 2
    assert len(document_vectors[0]) == len(query_vector)

    print("\nEmbedding test passed successfully.")


if __name__ == "__main__":
    main()


# uv run python -m tests.test_huggingface_embeddings