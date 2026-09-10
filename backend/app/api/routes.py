from pathlib import Path
from tempfile import (
    TemporaryDirectory,
)

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
)

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_database_session_dependency,
    get_embedding_provider_dependency,
    get_llm_provider_dependency,
    require_document_read_access,
    require_document_write_access,
)
from backend.app.api.schemas import (
    DocumentUploadResponse,
    HealthResponse,
    RAGQueryRequest,
    RAGQueryResponse,
    RAGSourceResponse,
)
from backend.app.core.config import (
    settings,
)
from backend.app.core.exceptions import (
    InvalidUploadError,
)
from backend.app.database.repositories import (
    DocumentRepository,
)
from backend.app.generation import (
    GroundedAnswerService,
)
from backend.app.ingestion.loaders.pdf_loader import (
    PDFDocumentLoader,
)
from backend.app.ingestion.parsers.pdf_parser import (
    PDFDocumentParser,
)
from backend.app.ingestion.processors.chunker import (
    DocumentChunker,
)
from backend.app.ingestion.processors.text_cleaner import (
    TextCleaner,
)
from backend.app.rate_limiting.dependencies import (
    require_user_rate_limit,
)
from backend.app.retrieval import (
    RetrievalService,
)
from backend.app.services.document_ingestion import (
    DocumentIngestionService,
)
from backend.app.services.rag_query import (
    RAGQueryService,
)
from backend.app.vectorstores.factory import (
    get_vector_store,
)


router = APIRouter(
    prefix=settings.api_prefix,
    tags=["RAG API"],
)


# =============================================================
# Step 35B — endpoint-specific limits
# =============================================================


upload_rate_limit = (
    require_user_rate_limit(
        scope="document-upload",
        limit=(
            settings
            .rate_limit_upload_requests
        ),
        window_seconds=(
            settings
            .rate_limit_upload_window_seconds
        ),
    )
)


rag_query_rate_limit = (
    require_user_rate_limit(
        scope="rag-query",
        limit=(
            settings
            .rate_limit_rag_requests
        ),
        window_seconds=(
            settings
            .rate_limit_rag_window_seconds
        ),
    )
)


# =============================================================
# Health
# =============================================================


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        application=(
            settings.app_name
        ),
        environment=(
            settings.app_environment
        ),
    )


# =============================================================
# Document upload
# =============================================================


@router.post(
    "/documents",
    response_model=(
        DocumentUploadResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
    dependencies=[
        Depends(
            upload_rate_limit
        ),
    ],
)
async def upload_document(
    knowledge_base_id: str = Form(
        ...
    ),
    file: UploadFile = File(
        ...
    ),
    access: OrganizationAccess = Depends(
        require_document_write_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
    embedding_provider=Depends(
        get_embedding_provider_dependency
    ),
) -> DocumentUploadResponse:
    validate_pdf_upload(
        file
    )

    with TemporaryDirectory(
        prefix="rag_upload_"
    ) as temporary_directory:
        safe_filename = Path(
            file.filename
            or "document.pdf"
        ).name

        temporary_path = (
            Path(
                temporary_directory
            )
            / safe_filename
        )

        await save_upload_to_temp_file(
            file=file,
            destination=(
                temporary_path
            ),
        )

        vector_store = (
            get_vector_store(
                embedding_provider=(
                    embedding_provider
                ),
                organization_id=(
                    access.organization_id
                ),
                user_id=(
                    access.user_id
                ),
                knowledge_base_id=(
                    knowledge_base_id
                ),
            )
        )

        repository = (
            DocumentRepository(
                session
            )
        )

        embedding_model_name = str(
            getattr(
                embedding_provider,
                "model_name",
                None,
            )
            or getattr(
                embedding_provider,
                "_model_name",
                None,
            )
            or settings.embedding_model_name
        )

        ingestion_service = (
            DocumentIngestionService(
                session=session,
                repository=repository,
                loader=(
                    PDFDocumentLoader()
                ),
                parser=(
                    PDFDocumentParser()
                ),
                cleaner=TextCleaner(),
                chunker=(
                    DocumentChunker()
                ),
                vector_store=(
                    vector_store
                ),
                embedding_provider_name=(
                    type(
                        embedding_provider
                    ).__name__
                ),
                embedding_model_name=(
                    embedding_model_name
                ),
                embedding_dimension=384,
                vector_store_provider_name=(
                    type(
                        vector_store
                    ).__name__
                ),
            )
        )

        result = (
            await ingestion_service
            .ingest_pdf(
                file_path=(
                    temporary_path
                ),
                organization_id=(
                    access.organization_id
                ),
                user_id=(
                    access.user_id
                ),
                knowledge_base_id=(
                    knowledge_base_id
                ),
            )
        )

        return DocumentUploadResponse(
            document_id=(
                result.document_id
            ),
            status=result.status,
            filename=safe_filename,
            total_pages=(
                result.total_pages
            ),
            chunk_count=(
                result.chunk_count
            ),
            vector_count=len(
                result.vector_ids
            ),
        )


# =============================================================
# RAG query
# =============================================================


@router.post(
    "/rag/query",
    response_model=(
        RAGQueryResponse
    ),
    dependencies=[
        Depends(
            rag_query_rate_limit
        ),
    ],
)
async def rag_query(
    request: RAGQueryRequest,
    access: OrganizationAccess = Depends(
        require_document_read_access
    ),
    embedding_provider=Depends(
        get_embedding_provider_dependency
    ),
    llm_provider=Depends(
        get_llm_provider_dependency
    ),
) -> RAGQueryResponse:
    vector_store = get_vector_store(
        embedding_provider=(
            embedding_provider
        ),
        organization_id=(
            access.organization_id
        ),
        user_id=access.user_id,
        knowledge_base_id=(
            request.knowledge_base_id
        ),
    )

    retrieval_service = (
        RetrievalService(
            vector_store=vector_store,
            default_k=(
                settings
                .retrieval_top_k
            ),
            max_k=20,
        )
    )

    generation_service = (
        GroundedAnswerService(
            llm_provider=(
                llm_provider
            ),
            max_context_characters=(
                24_000
            ),
        )
    )

    rag_service = (
        RAGQueryService(
            retrieval_service=(
                retrieval_service
            ),
            generation_service=(
                generation_service
            ),
        )
    )

    result = await rag_service.answer(
        query=request.query,
        k=request.k,
        document_id=(
            request.document_id
        ),
    )

    return RAGQueryResponse(
        query=result.query,
        answer=result.answer,
        grounded=result.grounded,
        citations=list(
            result.citations
        ),
        sources=[
            RAGSourceResponse(
                citation_id=(
                    source.citation_id
                ),
                document_id=(
                    source.document_id
                ),
                chunk_id=(
                    source.chunk_id
                ),
                filename=(
                    source.filename
                ),
                page_number=(
                    source.page_number
                ),
            )
            for source
            in result.sources
        ],
        retrieved_chunk_count=(
            result
            .retrieved_chunk_count
        ),
    )


# =============================================================
# Upload validation
# =============================================================


def validate_pdf_upload(
    file: UploadFile,
) -> None:
    filename = (
        file.filename
        or ""
    )

    if not filename.lower().endswith(
        ".pdf"
    ):
        raise InvalidUploadError(
            message=(
                "Only PDF documents "
                "are accepted."
            ),
            details={
                "filename": filename,
                "content_type": (
                    file.content_type
                ),
            },
        )

    allowed_content_types = {
        "application/pdf",
        "application/x-pdf",
    }

    if (
        file.content_type
        not in allowed_content_types
    ):
        raise InvalidUploadError(
            message=(
                "Only PDF content types "
                "are accepted."
            ),
            details={
                "filename": filename,
                "content_type": (
                    file.content_type
                ),
            },
        )


# =============================================================
# Save temporary upload
# =============================================================


async def save_upload_to_temp_file(
    *,
    file: UploadFile,
    destination: Path,
) -> None:
    total_bytes = 0

    with destination.open(
        "wb"
    ) as temp_file:
        while True:
            chunk = await file.read(
                1024 * 1024
            )

            if not chunk:
                break

            total_bytes += len(
                chunk
            )

            if (
                total_bytes
                > settings.upload_max_bytes
            ):
                raise InvalidUploadError(
                    message=(
                        "The uploaded PDF "
                        "is too large."
                    ),
                    details={
                        "maximum_bytes": (
                            settings
                            .upload_max_bytes
                        ),
                        "received_bytes": (
                            total_bytes
                        ),
                    },
                )

            temp_file.write(
                chunk
            )

    if total_bytes == 0:
        destination.unlink(
            missing_ok=True
        )

        raise InvalidUploadError(
            message=(
                "The uploaded PDF "
                "is empty."
            )
        )