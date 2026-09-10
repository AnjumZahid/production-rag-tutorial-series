import asyncio
from hashlib import sha256
from uuid import uuid4

from sqlalchemy import select

from backend.app.core.exceptions import (
    DocumentNotFoundError,
)
from backend.app.database.enums import (
    DocumentStatus,
)
from backend.app.database.models import (
    DocumentChunkRecord,
)
from backend.app.database.repositories import (
    ChunkReference,
    DocumentRepository,
)
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.services.document_management import (
    DocumentManagementService,
)


class FakeVectorStore:
    """
    Fake vector store used to verify exactly
    which vector IDs are deleted.
    """

    def __init__(self) -> None:
        self.deleted_ids: list[str] = []

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:
        self.deleted_ids.extend(
            chunk_ids
        )


async def main() -> None:
    print(
        "\n=== DOCUMENT MANAGEMENT TEST ==="
    )

    unique_value = uuid4().hex

    organization_id = (
        f"document-management-org-"
        f"{unique_value[:8]}"
    )

    user_id = (
        f"document-management-user-"
        f"{unique_value[8:16]}"
    )

    other_user_id = (
        f"other-user-"
        f"{unique_value[16:24]}"
    )

    other_organization_id = (
        f"other-org-"
        f"{unique_value[24:32]}"
    )

    knowledge_base_id = (
        f"document-management-kb-"
        f"{unique_value[:8]}"
    )

    file_hash = sha256(
        (
            f"document-{unique_value}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    chunk_id = sha256(
        (
            f"chunk-{unique_value}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    vector_id = sha256(
        (
            f"{organization_id}:"
            f"{user_id}:"
            f"{knowledge_base_id}:"
            f"{chunk_id}"
        ).encode(
            "utf-8"
        )
    ).hexdigest()

    session_factory = (
        get_session_factory()
    )

    document_id: str | None = None

    try:
        # -----------------------------------------------------
        # 1. Create temporary document
        # -----------------------------------------------------

        async with session_factory() as session:
            repository = (
                DocumentRepository(
                    session
                )
            )

            document = (
                await repository.create_document(
                    organization_id=(
                        organization_id
                    ),
                    user_id=user_id,
                    knowledge_base_id=(
                        knowledge_base_id
                    ),
                    filename=(
                        "management-test.pdf"
                    ),
                    file_hash=file_hash,
                    file_size_bytes=1024,
                    total_pages=3,
                )
            )

            document_id = document.id

            # -------------------------------------------------
            # Create one MySQL chunk reference
            # -------------------------------------------------

            await repository.add_chunk_references(
                document_id=document.id,
                organization_id=(
                    organization_id
                ),
                user_id=user_id,
                chunk_references=[
                    ChunkReference(
                        chunk_id=chunk_id,
                        vector_id=vector_id,
                        page_number=1,
                        chunk_index=0,
                    )
                ],
            )

            # -------------------------------------------------
            # Mark ingestion completed
            # -------------------------------------------------

            await repository.update_status(
                document_id=document.id,
                organization_id=(
                    organization_id
                ),
                user_id=user_id,
                status=(
                    DocumentStatus.COMPLETED
                ),
                embedding_provider=(
                    "huggingface"
                ),
                embedding_model=(
                    "sentence-transformers/"
                    "all-MiniLM-L6-v2"
                ),
                embedding_dimension=384,
                vector_store_provider=(
                    "chroma"
                ),
                total_pages=3,
            )

            await session.commit()

        # -----------------------------------------------------
        # Fake Chroma vector store
        # -----------------------------------------------------

        fake_vector_store = (
            FakeVectorStore()
        )

        # -----------------------------------------------------
        # 2. Test management service
        # -----------------------------------------------------

        async with session_factory() as session:
            repository = (
                DocumentRepository(
                    session
                )
            )

            service = (
                DocumentManagementService(
                    session=session,
                    repository=repository,
                )
            )

            # -------------------------------------------------
            # List documents
            # -------------------------------------------------

            listed = (
                await service.list_documents(
                    organization_id=(
                        organization_id
                    ),
                    user_id=user_id,
                    knowledge_base_id=(
                        knowledge_base_id
                    ),
                    offset=0,
                    limit=50,
                )
            )

            assert listed.total == 1

            assert (
                len(listed.documents)
                == 1
            )

            assert (
                listed.documents[0].id
                == document_id
            )

            assert (
                listed.offset
                == 0
            )

            assert (
                listed.limit
                == 50
            )

            print(
                "Document listing confirmed."
            )

            print(
                "Document total count confirmed."
            )

            # -------------------------------------------------
            # Detail lookup
            # -------------------------------------------------

            detail = (
                await service.get_document(
                    document_id=(
                        document_id
                    ),
                    organization_id=(
                        organization_id
                    ),
                    user_id=user_id,
                )
            )

            assert (
                detail.filename
                == "management-test.pdf"
            )

            assert (
                detail.status
                == DocumentStatus.COMPLETED.value
            )

            assert (
                detail.chunk_count
                == 1
            )

            assert (
                detail.total_pages
                == 3
            )

            print(
                "Document detail confirmed."
            )

            # -------------------------------------------------
            # Cross-user isolation
            # -------------------------------------------------

            other_user_list = (
                await service.list_documents(
                    organization_id=(
                        organization_id
                    ),
                    user_id=other_user_id,
                    knowledge_base_id=(
                        knowledge_base_id
                    ),
                    offset=0,
                    limit=50,
                )
            )

            assert (
                other_user_list.total
                == 0
            )

            assert (
                len(
                    other_user_list.documents
                )
                == 0
            )

            try:
                await service.get_document(
                    document_id=document_id,
                    organization_id=(
                        organization_id
                    ),
                    user_id=other_user_id,
                )

                raise AssertionError(
                    "Cross-user document access "
                    "should have been rejected."
                )

            except DocumentNotFoundError:
                pass

            print(
                "Cross-user isolation confirmed."
            )

            # -------------------------------------------------
            # Cross-organization isolation
            # -------------------------------------------------

            try:
                await service.get_document(
                    document_id=document_id,
                    organization_id=(
                        other_organization_id
                    ),
                    user_id=user_id,
                )

                raise AssertionError(
                    "Cross-organization document access "
                    "should have been rejected."
                )

            except DocumentNotFoundError:
                pass

            print(
                "Cross-organization isolation confirmed."
            )

            # -------------------------------------------------
            # Delete document
            # -------------------------------------------------

            await service.delete_document(
                document_id=document_id,
                organization_id=(
                    organization_id
                ),
                user_id=user_id,
                vector_store=(
                    fake_vector_store
                ),
            )

            # -------------------------------------------------
            # Verify vector deletion
            # -------------------------------------------------

            assert (
                fake_vector_store.deleted_ids
                == [vector_id]
            )

            print(
                "Chroma vector deletion confirmed."
            )

            # -------------------------------------------------
            # Verify MySQL document deletion
            # -------------------------------------------------

            deleted_document = (
                await repository.get_by_id(
                    document_id=document_id,
                    organization_id=(
                        organization_id
                    ),
                    user_id=user_id,
                )
            )

            assert (
                deleted_document
                is None
            )

            print(
                "MySQL document deletion confirmed."
            )

            # -------------------------------------------------
            # Verify chunk-reference cascade deletion
            # -------------------------------------------------

            chunk_statement = (
                select(
                    DocumentChunkRecord
                )
                .where(
                    DocumentChunkRecord.vector_id
                    == vector_id
                )
            )

            chunk_result = (
                await session.execute(
                    chunk_statement
                )
            )

            deleted_chunk = (
                chunk_result.scalar_one_or_none()
            )

            assert (
                deleted_chunk
                is None
            )

            print(
                "MySQL chunk-reference "
                "cascade deletion confirmed."
            )

            # -------------------------------------------------
            # Verify detail is now 404
            # -------------------------------------------------

            try:
                await service.get_document(
                    document_id=document_id,
                    organization_id=(
                        organization_id
                    ),
                    user_id=user_id,
                )

                raise AssertionError(
                    "Deleted document should "
                    "not be accessible."
                )

            except DocumentNotFoundError:
                pass

            print(
                "Post-deletion 404 confirmed."
            )

            document_id = None

            print(
                "Document management test "
                "passed successfully."
            )

    finally:
        # -----------------------------------------------------
        # Emergency cleanup if assertion/test fails
        # -----------------------------------------------------

        if document_id is not None:
            async with (
                session_factory()
                as cleanup_session
            ):
                cleanup_repository = (
                    DocumentRepository(
                        cleanup_session
                    )
                )

                existing = (
                    await cleanup_repository
                    .get_by_id(
                        document_id=document_id,
                        organization_id=(
                            organization_id
                        ),
                        user_id=user_id,
                    )
                )

                if existing is not None:
                    await (
                        cleanup_repository
                        .delete_document_record(
                            document_id=(
                                document_id
                            ),
                            organization_id=(
                                organization_id
                            ),
                            user_id=user_id,
                        )
                    )

                    await (
                        cleanup_session.commit()
                    )

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(
        main()
    )


# uv run python -m tests.test_document_management