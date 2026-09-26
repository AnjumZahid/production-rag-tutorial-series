from typing import Any


class AppError(Exception):
    """Base exception for controlled application errors."""

    code: str = "APPLICATION_ERROR"
    default_message: str = "An application error occurred."
    status_code: int = 500

    def __init__(
        self,
        message: str | None = None,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(AppError):
    code = "CONFIGURATION_ERROR"
    default_message = "The application configuration is invalid."
    status_code = 500


class DocumentError(AppError):
    code = "DOCUMENT_ERROR"
    default_message = "The document could not be processed."
    status_code = 422


class DocumentNotFoundError(DocumentError):
    code = "DOCUMENT_NOT_FOUND"
    default_message = "The requested document was not found."
    status_code = 404


class UnsupportedDocumentTypeError(DocumentError):
    code = "UNSUPPORTED_DOCUMENT_TYPE"
    default_message = "The document type is not supported."
    status_code = 415


class DocumentParsingError(DocumentError):
    code = "DOCUMENT_PARSING_FAILED"
    default_message = "The document content could not be extracted."
    status_code = 422

class DocumentChunkingError(AppError):
    code = "DOCUMENT_CHUNKING_FAILED"
    default_message = "The document could not be split into chunks."
    status_code = 422

class DocumentMetadataError(DocumentError):
    code = "DOCUMENT_METADATA_FAILED"
    default_message = "Document metadata could not be prepared."
    status_code = 422

class EmbeddingError(AppError):
    code = "EMBEDDING_FAILED"
    default_message = "Text could not be converted into embeddings."
    status_code = 500

class VectorStoreError(AppError):
    code = "VECTOR_STORE_ERROR"
    default_message = "The vector store operation failed."
    status_code = 500

class DatabaseError(AppError):
    code = "DATABASE_ERROR"
    default_message = "A database operation failed."
    status_code = 500

class DatabaseConnectionError(DatabaseError):
    code = "DATABASE_CONNECTION_ERROR"
    default_message = "The application could not connect to the database."
    status_code = 503

class DuplicateDocumentError(AppError):
    code = "DUPLICATE_DOCUMENT"
    default_message = (
        "This document has already been uploaded "
        "to the selected knowledge base."
    )
    status_code = 409

class DocumentIngestionError(AppError):
    code = "DOCUMENT_INGESTION_ERROR"
    default_message = "The document could not be ingested."
    status_code = 500

class InvalidQueryError(AppError):
    code = "INVALID_QUERY"
    default_message = "The retrieval query is invalid."
    status_code = 422


class RetrievalError(AppError):
    code = "RETRIEVAL_ERROR"
    default_message = "Relevant document context could not be retrieved."
    status_code = 500

class GenerationError(AppError):
    code = "GENERATION_ERROR"
    default_message = "A grounded answer could not be generated."
    status_code = 500

class LLMProviderError(AppError):
    code = "LLM_PROVIDER_ERROR"
    default_message = "The language-model provider request failed."
    status_code = 503


# uv run python -c "from backend.app.core.exceptions import DocumentNotFoundError; error = DocumentNotFoundError(details={'path': 'docs/sample.pdf'}); print(error.code); print(error.status_code); print(error); print(error.details)"