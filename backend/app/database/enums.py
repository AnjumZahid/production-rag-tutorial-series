from enum import StrEnum


class DocumentStatus(StrEnum):
    """Possible states of the document ingestion process."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DELETING = "deleting"