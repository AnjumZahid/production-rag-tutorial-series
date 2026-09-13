# import random
# import time
# from collections.abc import Iterator

# import tiktoken
# from openai import (
#     APIConnectionError,
#     APIError,
#     APITimeoutError,
#     AuthenticationError,
#     BadRequestError,
#     InternalServerError,
#     OpenAI,
#     PermissionDeniedError,
#     RateLimitError,
# )

# from backend.app.core.config import settings
# from backend.app.core.exceptions import EmbeddingError
# from backend.app.core.logging import get_logger
# from backend.app.embeddings.base import BaseEmbeddingProvider


# logger = get_logger(__name__)


# class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
#     """
#     Create embeddings through the OpenAI API.

#     Document texts are divided into safe sequential batches based on:
#     - maximum texts per request
#     - maximum tokens per input
#     - maximum combined tokens per request

#     Temporary failures are retried using exponential backoff and jitter.
#     """

#     def __init__(
#         self,
#         model_name: str | None = None,
#     ) -> None:
#         if settings.openai_api_key is None:
#             raise EmbeddingError(
#                 message=(
#                     "The OpenAI API key is missing. "
#                     "Set OPENAI_API_KEY in the .env file."
#                 )
#             )

#         self._model_name = (
#             model_name or settings.openai_embedding_model
#         )

#         api_key = settings.openai_api_key.get_secret_value()

#         try:
#             self._encoding = tiktoken.encoding_for_model(
#                 self._model_name
#             )
#         except KeyError:
#             # Safe fallback for models not registered in tiktoken.
#             self._encoding = tiktoken.get_encoding("cl100k_base")

#         try:
#             self._client = OpenAI(
#                 api_key=api_key,
#                 timeout=settings.openai_timeout_seconds,

#                 # We perform our own retry handling so that batch number,
#                 # delay and failure details can be logged clearly.
#                 max_retries=0,
#             )
#         except Exception as exc:
#             raise EmbeddingError(
#                 message="The OpenAI client could not be created.",
#                 details={
#                     "error_type": type(exc).__name__,
#                 },
#             ) from exc

#         logger.info(
#             "openai_embedding_provider_initialized",
#             provider=self.provider_name,
#             model=self.model_name,
#             batch_size=settings.openai_embedding_batch_size,
#         )

#     @property
#     def provider_name(self) -> str:
#         return "openai"

#     @property
#     def model_name(self) -> str:
#         return self._model_name

#     def embed_documents(
#         self,
#         texts: list[str],
#     ) -> list[list[float]]:
#         if not texts:
#             raise EmbeddingError(
#                 message="No document texts were provided for embedding."
#             )

#         cleaned_texts = [text.strip() for text in texts]

#         empty_positions = [
#             position
#             for position, text in enumerate(cleaned_texts, start=1)
#             if not text
#         ]

#         if empty_positions:
#             raise EmbeddingError(
#                 message="Empty document text cannot be embedded.",
#                 details={
#                     "empty_positions": empty_positions[:20],
#                 },
#             )

#         batches = list(self._create_batches(cleaned_texts))

#         logger.info(
#             "openai_document_embedding_started",
#             document_count=len(cleaned_texts),
#             batch_count=len(batches),
#             model=self.model_name,
#         )

#         all_vectors: list[list[float]] = []

#         for batch_number, batch in enumerate(batches, start=1):
#             logger.info(
#                 "openai_embedding_batch_started",
#                 batch_number=batch_number,
#                 batch_count=len(batches),
#                 text_count=len(batch),
#             )

#             batch_vectors = self._request_embeddings(
#                 batch,
#                 operation="embed_documents",
#                 batch_number=batch_number,
#             )

#             all_vectors.extend(batch_vectors)

#             logger.info(
#                 "openai_embedding_batch_completed",
#                 batch_number=batch_number,
#                 vector_count=len(batch_vectors),
#             )

#             # Avoid sending all batches immediately one after another.
#             if (
#                 batch_number < len(batches)
#                 and settings.openai_embedding_batch_delay > 0
#             ):
#                 time.sleep(
#                     settings.openai_embedding_batch_delay
#                 )

#         if len(all_vectors) != len(cleaned_texts):
#             raise EmbeddingError(
#                 message=(
#                     "The number of returned vectors does not match "
#                     "the number of document texts."
#                 ),
#                 details={
#                     "text_count": len(cleaned_texts),
#                     "vector_count": len(all_vectors),
#                 },
#             )

#         logger.info(
#             "openai_document_embedding_completed",
#             document_count=len(cleaned_texts),
#             vector_count=len(all_vectors),
#             vector_dimension=len(all_vectors[0]),
#         )

#         return all_vectors

#     def embed_query(
#         self,
#         text: str,
#     ) -> list[float]:
#         cleaned_text = text.strip()

#         if not cleaned_text:
#             raise EmbeddingError(
#                 message="An empty query cannot be embedded."
#             )

#         token_count = self._count_tokens(cleaned_text)

#         if token_count > settings.openai_embedding_max_input_tokens:
#             raise EmbeddingError(
#                 message="The query exceeds the configured token limit.",
#                 details={
#                     "token_count": token_count,
#                     "maximum_tokens": (
#                         settings.openai_embedding_max_input_tokens
#                     ),
#                 },
#             )

#         logger.info(
#             "openai_query_embedding_started",
#             model=self.model_name,
#             token_count=token_count,
#         )

#         vectors = self._request_embeddings(
#             [cleaned_text],
#             operation="embed_query",
#             batch_number=1,
#         )

#         vector = vectors[0]

#         logger.info(
#             "openai_query_embedding_completed",
#             vector_dimension=len(vector),
#         )

#         return vector

#     def _create_batches(
#         self,
#         texts: list[str],
#     ) -> Iterator[list[str]]:
#         """
#         Create batches constrained by both text count and token count.
#         """

#         current_batch: list[str] = []
#         current_token_count = 0

#         for position, text in enumerate(texts, start=1):
#             text_token_count = self._count_tokens(text)

#             if (
#                 text_token_count
#                 > settings.openai_embedding_max_input_tokens
#             ):
#                 raise EmbeddingError(
#                     message=(
#                         "A document chunk exceeds the configured "
#                         "OpenAI input-token limit."
#                     ),
#                     details={
#                         "position": position,
#                         "token_count": text_token_count,
#                         "maximum_tokens": (
#                             settings.openai_embedding_max_input_tokens
#                         ),
#                     },
#                 )

#             exceeds_item_limit = (
#                 len(current_batch)
#                 >= settings.openai_embedding_batch_size
#             )

#             exceeds_token_limit = (
#                 current_batch
#                 and (
#                     current_token_count + text_token_count
#                     > settings.openai_embedding_max_batch_tokens
#                 )
#             )

#             if exceeds_item_limit or exceeds_token_limit:
#                 yield current_batch
#                 current_batch = []
#                 current_token_count = 0

#             current_batch.append(text)
#             current_token_count += text_token_count

#         if current_batch:
#             yield current_batch

#     def _request_embeddings(
#         self,
#         texts: list[str],
#         *,
#         operation: str,
#         batch_number: int,
#     ) -> list[list[float]]:
#         request_parameters: dict[str, object] = {
#             "model": self.model_name,
#             "input": texts,
#             "encoding_format": "float",
#         }

#         if settings.openai_embedding_dimensions is not None:
#             request_parameters["dimensions"] = (
#                 settings.openai_embedding_dimensions
#             )

#         maximum_attempts = (
#             settings.openai_embedding_max_retries + 1
#         )

#         for attempt in range(1, maximum_attempts + 1):
#             try:
#                 response = self._client.embeddings.create(
#                     **request_parameters
#                 )

#                 # Ensure vectors remain in the same order as inputs.
#                 ordered_items = sorted(
#                     response.data,
#                     key=lambda item: item.index,
#                 )

#                 vectors = [
#                     item.embedding
#                     for item in ordered_items
#                 ]

#                 if len(vectors) != len(texts):
#                     raise EmbeddingError(
#                         message=(
#                             "OpenAI returned an unexpected number "
#                             "of embedding vectors."
#                         ),
#                         details={
#                             "input_count": len(texts),
#                             "vector_count": len(vectors),
#                         },
#                     )

#                 return vectors

#             except AuthenticationError as exc:
#                 raise EmbeddingError(
#                     message=(
#                         "OpenAI authentication failed. "
#                         "Check OPENAI_API_KEY."
#                     ),
#                     details={
#                         "operation": operation,
#                         "request_id": getattr(
#                             exc,
#                             "request_id",
#                             None,
#                         ),
#                     },
#                 ) from exc

#             except PermissionDeniedError as exc:
#                 raise EmbeddingError(
#                     message=(
#                         "The OpenAI API key does not have permission "
#                         "to use this embedding model."
#                     ),
#                     details={
#                         "model": self.model_name,
#                         "request_id": getattr(
#                             exc,
#                             "request_id",
#                             None,
#                         ),
#                     },
#                 ) from exc

#             except BadRequestError as exc:
#                 raise EmbeddingError(
#                     message=(
#                         "OpenAI rejected the embedding request."
#                     ),
#                     details={
#                         "operation": operation,
#                         "model": self.model_name,
#                         "request_id": getattr(
#                             exc,
#                             "request_id",
#                             None,
#                         ),
#                     },
#                 ) from exc

#             except (
#                 RateLimitError,
#                 APITimeoutError,
#                 APIConnectionError,
#                 InternalServerError,
#             ) as exc:
#                 if attempt >= maximum_attempts:
#                     raise EmbeddingError(
#                         message=(
#                             "The OpenAI embedding request failed "
#                             "after all retry attempts."
#                         ),
#                         details={
#                             "operation": operation,
#                             "batch_number": batch_number,
#                             "attempts": attempt,
#                             "error_type": type(exc).__name__,
#                             "request_id": getattr(
#                                 exc,
#                                 "request_id",
#                                 None,
#                             ),
#                         },
#                     ) from exc

#                 delay = min(
#                     settings.openai_embedding_max_retry_delay,
#                     (
#                         settings.openai_embedding_initial_retry_delay
#                         * (2 ** (attempt - 1))
#                     ),
#                 )

#                 # Jitter prevents many workers retrying simultaneously.
#                 delay += random.uniform(
#                     0,
#                     min(1.0, delay * 0.25),
#                 )

#                 logger.warning(
#                     "openai_embedding_request_retrying",
#                     operation=operation,
#                     batch_number=batch_number,
#                     attempt=attempt,
#                     next_attempt=attempt + 1,
#                     delay_seconds=round(delay, 2),
#                     error_type=type(exc).__name__,
#                 )

#                 time.sleep(delay)

#             except EmbeddingError:
#                 raise

#             except APIError as exc:
#                 raise EmbeddingError(
#                     message="The OpenAI embedding API returned an error.",
#                     details={
#                         "operation": operation,
#                         "error_type": type(exc).__name__,
#                         "request_id": getattr(
#                             exc,
#                             "request_id",
#                             None,
#                         ),
#                     },
#                 ) from exc

#             except Exception as exc:
#                 raise EmbeddingError(
#                     message=(
#                         "An unexpected OpenAI embedding error occurred."
#                     ),
#                     details={
#                         "operation": operation,
#                         "error_type": type(exc).__name__,
#                     },
#                 ) from exc

#         raise EmbeddingError(
#             message="The OpenAI embedding request did not complete."
#         )

#     def _count_tokens(self, text: str) -> int:
#         return len(
#             self._encoding.encode(
#                 text,
#                 disallowed_special=(),
#             )
#         )

