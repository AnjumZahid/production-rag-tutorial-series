# ```python
# """
# EMBEDDING PROVIDER FACTORY NOTES

# Purpose:
# - This file selects which embedding provider the application should use.
# - It creates the correct provider object based on application settings.

# Why a factory is needed:
# - The project may support multiple embedding providers.
# - Examples:
#     Hugging Face
#     OpenAI
#     Cohere
#     Local custom model

# Without a factory:
# - Different parts of the application may directly create provider classes.
# - Switching providers would require changing code in many files.

# With a factory:
# - The application asks for one embedding provider.
# - The factory reads the configuration.
# - The factory creates the selected provider.
# - The rest of the RAG pipeline remains unchanged.


# Configuration example:

#     EMBEDDING_PROVIDER=huggingface

# or:

#     EMBEDDING_PROVIDER=openai


# Main function:

#     get_embedding_provider()

# This function:
# 1. Reads settings.embedding_provider.
# 2. Compares the configured value.
# 3. Creates the matching provider class.
# 4. Returns it as BaseEmbeddingProvider.


# Example:

#     provider = get_embedding_provider()

# If configuration is:

#     EMBEDDING_PROVIDER=huggingface

# the factory returns:

#     HuggingFaceEmbeddingProvider()


# If configuration is:

#     EMBEDDING_PROVIDER=openai

# the factory returns:

#     OpenAIEmbeddingProvider()


# Important:
# - The application does not directly run huggingface.py or openai.py.
# - The normal application pipeline calls get_embedding_provider().
# - The factory imports and creates the selected class.
# - Only the selected provider object is used.


# Why the return type is BaseEmbeddingProvider:
# - Every provider follows the same interface.
# - The calling code only needs:
#     embed_documents()
#     embed_query()
#     provider_name
#     model_name

# The calling code does not need to know whether the provider is:
# - Hugging Face
# - OpenAI
# - another provider


# Example application code:

#     provider = get_embedding_provider()
#     vectors = provider.embed_documents(texts)

# This same code works for all supported providers.


# Unsupported provider:
# - If the configured provider name is unknown, the factory raises an error.
# - This prevents the application from silently using the wrong provider.


# Flow:

#     Application starts
#         ->
#     calls get_embedding_provider()
#         ->
#     reads EMBEDDING_PROVIDER
#         ->
#     creates selected provider
#         ->
#     returns provider to RAG pipeline


# Benefits:
# - Easy provider switching.
# - Cleaner application code.
# - Centralized provider selection.
# - Better testing.
# - Easier future expansion.
# """
# ```



# backend/app/embeddings/factory.py

from backend.app.core.config import settings
from backend.app.embeddings.base import BaseEmbeddingProvider
from backend.app.embeddings.huggingface import HuggingFaceEmbeddingProvider
from backend.app.embeddings.openai import OpenAIEmbeddingProvider


def get_embedding_provider() -> BaseEmbeddingProvider:
    if settings.embedding_provider == "huggingface":
        return HuggingFaceEmbeddingProvider()

    if settings.embedding_provider == "openai":
        return OpenAIEmbeddingProvider()

    raise ValueError(
        f"Unsupported embedding provider: {settings.embedding_provider}"
    )

