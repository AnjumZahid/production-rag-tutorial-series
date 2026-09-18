from abc import abstractmethod

from langchain_core.embeddings import Embeddings


class BaseEmbeddingProvider(Embeddings):
    """Common interface for all embedding-model providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the embedding provider name."""
        raise NotImplementedError

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the embedding model name."""
        raise NotImplementedError

    @abstractmethod
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Convert multiple document texts into vectors."""
        raise NotImplementedError

    @abstractmethod
    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Convert one user query into a vector."""
        raise NotImplementedError
    
# uv run python -c "from backend.app.embeddings.base import BaseEmbeddingProvider; print('BaseEmbeddingProvider imported successfully')"