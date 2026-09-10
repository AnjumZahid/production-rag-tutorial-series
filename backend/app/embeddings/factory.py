# backend/app/embeddings/factory.py

from backend.app.core.config import settings
from backend.app.embeddings.base import BaseEmbeddingProvider
from backend.app.embeddings.huggingface import HuggingFaceEmbeddingProvider
# from backend.app.embeddings.openai import OpenAIEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    if settings.embedding_provider == "huggingface":
        return HuggingFaceEmbeddingProvider()

    # if settings.embedding_provider == "openai":
    #     return OpenAIEmbeddingProvider()

    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )

