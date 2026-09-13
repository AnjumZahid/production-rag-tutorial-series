# ```python
# """
# BASE EMBEDDING PROVIDER NOTES

# Purpose:
# - This file defines a common contract for every embedding provider.
# - It does not create real embeddings by itself.
# - It only defines what every embedding provider must implement.

# Why it is needed:
# - Later we may use OpenAI, Hugging Face, Cohere, or a local model.
# - All providers should follow the same method names and return format.
# - This lets us change the embedding provider without changing the RAG pipeline.

# What is an embedding?
# - An embedding converts text into a list of numbers called a vector.
# - Texts with similar meanings usually receive similar vectors.

# Example:

#     "High blood pressure affects the heart"

# becomes something like:

#     [0.12, -0.34, 0.78, ...]

# How this class works:
# - BaseEmbeddingProvider inherits from LangChain's Embeddings interface.
# - It is an abstract base class.
# - Child provider classes must implement all abstract properties and methods.

# provider_name:
# - Returns the provider name.

# Example:
#     "openai"
#     "huggingface"

# model_name:
# - Returns the exact embedding model name.

# Example:
#     "text-embedding-3-small"
#     "all-MiniLM-L6-v2"

# embed_documents(texts):
# - Receives multiple document chunk texts.
# - Returns one vector for every chunk.

# Input:

#     [
#         "Chunk 1 text",
#         "Chunk 2 text"
#     ]

# Output:

#     [
#         [0.1, 0.2, ...],
#         [0.7, 0.3, ...]
#     ]

# These document vectors will later be stored in Chroma.

# embed_query(text):
# - Receives one user question.
# - Returns one vector for that question.

# Input:

#     "What causes high blood pressure?"

# Output:

#     [0.15, 0.22, ...]

# Why documents and query have separate methods:
# - Document chunks are usually embedded in batches.
# - A user question is normally embedded one at a time.
# - Some embedding models treat documents and queries differently.
# - LangChain therefore keeps both operations separate.

# Flow:

#     Document chunks
#         ->
#     embed_documents()
#         ->
#     document vectors
#         ->
#     Chroma storage

#     User question
#         ->
#     embed_query()
#         ->
#     query vector
#         ->
#     similarity search in Chroma

# Important:
# - This base class is only a blueprint.
# - A real provider class will contain the actual model or API logic.
# - It does not store vectors.
# - It does not retrieve documents.
# - It does not call the final answer-generating LLM.
# """
# ```


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