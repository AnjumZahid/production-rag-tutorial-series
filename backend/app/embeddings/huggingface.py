# ```python
# """
# HUGGING FACE EMBEDDING PROVIDER NOTES

# Purpose:
# - This file provides the real embedding implementation for Hugging Face models.
# - It converts document text and user queries into numerical vectors.
# - It follows the common BaseEmbeddingProvider interface.

# Why this file is needed:
# - base.py only defines the required methods.
# - huggingface.py contains the actual Hugging Face model-loading and embedding logic.

# Main class:
#     HuggingFaceEmbeddingProvider

# The class inherits:
#     BaseEmbeddingProvider

# Therefore it must implement:
# - provider_name
# - model_name
# - embed_documents()
# - embed_query()


# Model configuration:
# - The model name comes from settings.embedding_model_name.
# - The device comes from settings.embedding_device.
# - The device can normally be:
#     "cpu"
#     "cuda"

# Example model:
#     sentence-transformers/all-MiniLM-L6-v2


# __init__ method:
# - Selects the configured model and device.
# - Loads HuggingFaceEmbeddings.
# - Applies batch-size and normalization settings.
# - Raises EmbeddingError if the model cannot be loaded.

# Important:
# - The model is loaded when HuggingFaceEmbeddingProvider() is created.
# - The first execution may download the model.
# - Later executions normally use the locally cached model.


# provider_name:
# - Returns:
#     "huggingface"

# model_name:
# - Returns the exact model currently being used.


# embed_documents(texts):
# - Receives multiple document chunk texts.
# - Removes beginning and ending spaces.
# - Rejects an empty list.
# - Rejects empty chunk text.
# - Returns one vector for each text.

# Example input:

#     [
#         "First document chunk",
#         "Second document chunk"
#     ]

# Example output:

#     [
#         [0.12, -0.30, 0.81, ...],
#         [0.45, 0.11, -0.24, ...]
#     ]


# embed_query(text):
# - Receives one user question.
# - Removes beginning and ending spaces.
# - Rejects an empty query.
# - Returns one query vector.

# Example input:

#     "What causes high blood pressure?"

# Example output:

#     [0.14, -0.27, 0.79, ...]


# normalize_embeddings:
# - When enabled, vectors are normalized to unit length.
# - This makes cosine-similarity comparison consistent.
# - It is useful for semantic search.


# batch_size:
# - Controls how many document texts are embedded together.
# - Larger batches can be faster but require more memory.


# Logging:
# - Logs when model loading starts and finishes.
# - Logs document-embedding operations.
# - Logs query-embedding operations.
# - Logs vector dimensions and item counts.


# Error handling:
# - Model-loading failures raise EmbeddingError.
# - Document embedding failures raise EmbeddingError.
# - Query embedding failures raise EmbeddingError.
# - The original exception is preserved using:
#     raise ... from exc


# Flow:

#     Clean document chunks
#         ->
#     HuggingFaceEmbeddingProvider.embed_documents()
#         ->
#     document vectors
#         ->
#     Chroma vector storage

#     User question
#         ->
#     HuggingFaceEmbeddingProvider.embed_query()
#         ->
#     query vector
#         ->
#     similarity search


# Important:
# - This file does not store vectors in Chroma.
# - It does not retrieve chunks.
# - It does not generate the final answer.
# - It only loads the embedding model and creates vectors.
# """
# ```


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