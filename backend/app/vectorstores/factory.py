from typing import Any

from backend.app.core.config import settings
from backend.app.core.exceptions import VectorStoreError
from backend.app.embeddings.base import BaseEmbeddingProvider


def get_vector_store(
    embedding_provider: BaseEmbeddingProvider,
    *,
    organization_id: str,
    user_id: str,
    knowledge_base_id: str,
) -> Any:
    """
    Create the vector-store provider selected in the .env file.

    VECTOR_STORE_PROVIDER=chroma
        -> ChromaVectorStore

    VECTOR_STORE_PROVIDER=qdrant
        -> QdrantVectorStore
    """

    provider_name = settings.vector_store_provider.strip().lower()

    if provider_name == "chroma":
        from backend.app.vectorstores.chroma_store import (
            ChromaVectorStore,
        )

        return ChromaVectorStore(
            embedding_provider=embedding_provider,
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )

    if provider_name == "qdrant":
        from backend.app.vectorstores.qdrant_store import (
            QdrantVectorStore,
        )

        return QdrantVectorStore(
            embedding_provider=embedding_provider,
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )

    raise VectorStoreError(
        message="Unsupported vector-store provider.",
        details={
            "provider": provider_name,
            "supported_providers": [
                "chroma",
                "qdrant",
            ],
        },
    )
