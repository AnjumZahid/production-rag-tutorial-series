# uv add langchain-huggingface sentence-transformers

from langchain_huggingface import HuggingFaceEmbeddings

from backend.app.core.config import settings
from backend.app.core.exceptions import EmbeddingError
from backend.app.core.logging import get_logger
from backend.app.embeddings.base import BaseEmbeddingProvider


logger = get_logger(__name__)


class HuggingFaceEmbeddingProvider(BaseEmbeddingProvider):
    """Create local text embeddings using a Hugging Face model."""

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self._model_name = model_name or settings.embedding_model_name
        self._device = device or settings.embedding_device

        logger.info(
            "embedding_model_loading_started",
            provider=self.provider_name,
            model=self._model_name,
            device=self._device,
        )

        try:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self._model_name,
                model_kwargs={
                    "device": self._device,
                },
                encode_kwargs={
                    "batch_size": settings.embedding_batch_size,
                    "normalize_embeddings": settings.embedding_normalize,
                },
            )
        except Exception as exc:
            raise EmbeddingError(
                message="The Hugging Face embedding model could not be loaded.",
                details={
                    "model": self._model_name,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        logger.info(
            "embedding_model_loading_completed",
            provider=self.provider_name,
            model=self._model_name,
            device=self._device,
        )

    @property
    def provider_name(self) -> str:
        return "huggingface"

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        if not texts:
            raise EmbeddingError(
                message="No document texts were provided for embedding."
            )

        cleaned_texts = [text.strip() for text in texts]

        if any(not text for text in cleaned_texts):
            raise EmbeddingError(
                message="Empty document text cannot be embedded."
            )

        logger.info(
            "document_embedding_started",
            document_count=len(cleaned_texts),
            model=self.model_name,
        )

        try:
            vectors = self._embeddings.embed_documents(cleaned_texts)
        except Exception as exc:
            raise EmbeddingError(
                details={
                    "operation": "embed_documents",
                    "error_type": type(exc).__name__,
                }
            ) from exc

        logger.info(
            "document_embedding_completed",
            document_count=len(vectors),
            vector_dimension=len(vectors[0]),
        )

        return vectors

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        cleaned_text = text.strip()

        if not cleaned_text:
            raise EmbeddingError(
                message="An empty query cannot be embedded."
            )

        logger.info(
            "query_embedding_started",
            model=self.model_name,
        )

        try:
            vector = self._embeddings.embed_query(cleaned_text)
        except Exception as exc:
            raise EmbeddingError(
                details={
                    "operation": "embed_query",
                    "error_type": type(exc).__name__,
                }
            ) from exc

        logger.info(
            "query_embedding_completed",
            vector_dimension=len(vector),
        )

        return vector
    

# importnant notes: if erroe occred due to not using hugging face TOKEN then you have to modify the code and add the functionality to process it with using hugging face TOKEN and that token in .env file which process through config file.

# check which model already present in machine.
# uv run python -c "from huggingface_hub import scan_cache_dir; cache=scan_cache_dir(); models=sorted([r for r in cache.repos if r.repo_type=='model'], key=lambda r:r.repo_id); [print(f'{r.repo_id} | {r.size_on_disk/1024**2:.2f} MB') for r in models]; print('No cached models found.' if not models else '')"