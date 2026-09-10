import asyncio

from fastapi import (
    APIRouter,
    Depends,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_database_session_dependency,
    get_embedding_provider_dependency,
    require_document_read_access,
    require_document_write_access,
)
from backend.app.api.document_schemas import (
    DocumentListResponse,
    DocumentResponse,
)
from backend.app.database.repositories import (
    DocumentRepository,
)
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
)
from backend.app.services.document_management import (
    DocumentManagementService,
    DocumentView,
)
from backend.app.vectorstores.factory import (
    get_vector_store,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------


def build_document_response(
    document: DocumentView,
) -> DocumentResponse:
    """
    Convert service-layer document view into
    FastAPI response schema.
    """

    return DocumentResponse(
        id=document.id,
        knowledge_base_id=(
            document.knowledge_base_id
        ),
        filename=document.filename,
        status=document.status,
        file_size_bytes=(
            document.file_size_bytes
        ),
        total_pages=document.total_pages,
        chunk_count=document.chunk_count,
        embedding_provider=(
            document.embedding_provider
        ),
        embedding_model=(
            document.embedding_model
        ),
        embedding_dimension=(
            document.embedding_dimension
        ),
        vector_store_provider=(
            document.vector_store_provider
        ),
        error_message=(
            document.error_message
        ),
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def build_document_service(
    session: AsyncSession,
) -> DocumentManagementService:
    """
    Build document-management service for one
    database session.
    """

    return DocumentManagementService(
        session=session,
        repository=DocumentRepository(
            session
        ),
    )


# ---------------------------------------------------------
# List documents
# ---------------------------------------------------------


@router.get(
    "",
    response_model=DocumentListResponse,
)
async def list_documents(
    access: OrganizationAccess = Depends(
        require_document_read_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
    knowledge_base_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=128,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
) -> DocumentListResponse:
    """
    List authenticated user's documents.

    Allowed roles:

        owner
        admin
        member
        viewer
    """

    service = build_document_service(
        session
    )

    result = await service.list_documents(
        organization_id=(
            access.organization_id
        ),
        user_id=access.user_id,
        knowledge_base_id=(
            knowledge_base_id
        ),
        offset=offset,
        limit=limit,
    )

    return DocumentListResponse(
        documents=[
            build_document_response(
                document
            )
            for document in result.documents
        ],
        total=result.total,
        offset=result.offset,
        limit=result.limit,
    )


# ---------------------------------------------------------
# Document detail
# ---------------------------------------------------------


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: str,
    access: OrganizationAccess = Depends(
        require_document_read_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> DocumentResponse:
    """
    Return one authenticated user-owned document.

    A document belonging to another organization/user
    behaves like a missing document and returns 404.
    """

    service = build_document_service(
        session
    )

    document = await service.get_document(
        document_id=document_id,
        organization_id=(
            access.organization_id
        ),
        user_id=access.user_id,
    )

    return build_document_response(
        document
    )


# ---------------------------------------------------------
# Delete document
# ---------------------------------------------------------


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    document_id: str,
    access: OrganizationAccess = Depends(
        require_document_write_access
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
    embedding_provider: BaseEmbeddingProvider = Depends(
        get_embedding_provider_dependency
    ),
) -> Response:
    """
    Delete document metadata, chunk references and vectors.

    Allowed roles:

        owner
        admin
        member

    Viewer is rejected by the existing
    require_document_write_access dependency.
    """

    service = build_document_service(
        session
    )

    # -----------------------------------------------------
    # First load the document so we know which
    # knowledge base owns its vector collection.
    # -----------------------------------------------------

    document = await service.get_document(
        document_id=document_id,
        organization_id=(
            access.organization_id
        ),
        user_id=access.user_id,
    )

    vector_store = get_vector_store(
        embedding_provider=(
            embedding_provider
        ),
        organization_id=(
            access.organization_id
        ),
        user_id=access.user_id,
        knowledge_base_id=(
            document.knowledge_base_id
        ),
    )

    try:
        await service.delete_document(
            document_id=document_id,
            organization_id=(
                access.organization_id
            ),
            user_id=access.user_id,
            vector_store=vector_store,
        )

    finally:
        # Chroma close is synchronous.
        close_method = getattr(
            vector_store,
            "close",
            None,
        )

        if callable(close_method):
            await asyncio.to_thread(
                close_method
            )

    return Response(
        status_code=(
            status.HTTP_204_NO_CONTENT
        )
    )