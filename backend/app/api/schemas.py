from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str
    application: str
    environment: str


class DocumentUploadResponse(BaseModel):
    document_id: str
    status: str
    filename: str
    total_pages: int
    chunk_count: int
    vector_count: int


class RAGQueryRequest(BaseModel):
    knowledge_base_id: str = Field(
        min_length=1,
        max_length=200,
    )
    query: str = Field(
        min_length=1,
        max_length=4000,
    )
    k: int | None = Field(
        default=None,
        ge=1,
        le=20,
    )
    document_id: str | None = None


class RAGSourceResponse(BaseModel):
    citation_id: str
    document_id: str | None
    chunk_id: str | None
    filename: str | None
    page_number: int | None


class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    grounded: bool
    citations: list[str]
    sources: list[RAGSourceResponse]
    retrieved_chunk_count: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail