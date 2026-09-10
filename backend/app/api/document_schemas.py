from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """
    Public document metadata returned by the API.
    """

    id: str
    knowledge_base_id: str
    filename: str
    status: str
    file_size_bytes: int
    total_pages: int | None
    chunk_count: int
    embedding_provider: str | None
    embedding_model: str | None
    embedding_dimension: int | None
    vector_store_provider: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """
    Paginated document-list response.
    """

    documents: list[DocumentResponse]
    total: int
    offset: int
    limit: int