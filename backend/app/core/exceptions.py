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




# uv run python -c "from backend.app.core.exceptions import DocumentNotFoundError; error = DocumentNotFoundError(details={'path': 'docs/sample.pdf'}); print(error.code); print(error.status_code); print(error); print(error.details)"