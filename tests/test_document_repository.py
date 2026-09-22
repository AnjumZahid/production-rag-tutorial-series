import asyncio
from hashlib import sha256
from uuid import uuid4

from backend.app.database.enums import DocumentStatus
from backend.app.database.repositories import (
    ChunkReference,
    DocumentRepository,
)
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)


async def main() -> None:
    unique_value = uuid4().hex

    organization_id = f"test-org-{unique_value[:8]}"
    user_id = f"test-user-{unique_value[8:16]}"
    knowledge_base_id = f"test-kb-{unique_value[16:24]}"

    file_content = f"temporary-test-file-{unique_value}"
    file_hash = sha256(file_content.encode("utf-8")).hexdigest()

    chunk_id = sha256(
        f"temporary-test-chunk-{unique_value}".encode("utf-8")
    ).hexdigest()

    vector_id = sha256(
        (
            f"{organization_id}:"
            f"{user_id}:"
            f"{knowledge_base_id}:"
            f"{chunk_id}"
        ).encode("utf-8")
    ).hexdigest()

    session_factory = get_session_factory()
    created_document_id: str | None = None

    try:
        async with session_factory() as session:
            repository = DocumentRepository(session)

            try:
                duplicate = await repository.get_by_hash(
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    file_hash=file_hash,
                )

                assert duplicate is None

                document = await repository.create_document(
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                    filename="temporary_test.pdf",
                    file_hash=file_hash,
                    file_size_bytes=len(file_content),
                    total_pages=1,
                )

                created_document_id = document.id

                assert document.status == DocumentStatus.PENDING.value

                chunk_records = await repository.add_chunk_references(
                    document_id=document.id,
                    organization_id=organization_id,
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

                assert len(chunk_records) == 1
                assert chunk_records[0].vector_id == vector_id

                updated_document = await repository.update_status(
                    document_id=document.id,
                    organization_id=organization_id,
                    user_id=user_id,
                    status=DocumentStatus.COMPLETED,
                    embedding_provider="huggingface",
                    embedding_model=(
                        "sentence-transformers/all-MiniLM-L6-v2"
                    ),
                    embedding_dimension=384,
                    vector_store_provider="chroma",
                )

                assert (
                    updated_document.status
                    == DocumentStatus.COMPLETED.value
                )
                assert updated_document.chunk_count == 1

                documents = await repository.list_documents(
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                )

                assert len(documents) == 1
                assert documents[0].id == document.id

                await session.commit()

                print("\n=== DOCUMENT REPOSITORY TEST ===")
                print("Document ID:", document.id)
                print("Status:", updated_document.status)
                print("Chunk count:", updated_document.chunk_count)
                print("Vector ID:", vector_id)

                deleted = await repository.delete_document_record(
                    document_id=document.id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert deleted is True

                await session.commit()

                deleted_document = await repository.get_by_id(
                    document_id=document.id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert deleted_document is None

                print("Document deletion confirmed.")
                print("Document repository test passed successfully.")

            finally:
                await session.rollback()

                if created_document_id is not None:
                    existing_document = await repository.get_by_id(
                        document_id=created_document_id,
                        organization_id=organization_id,
                        user_id=user_id,
                    )

                    if existing_document is not None:
                        await repository.delete_document_record(
                            document_id=created_document_id,
                            organization_id=organization_id,
                            user_id=user_id,
                        )
                        await session.commit()

    finally:
        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())

# uv run python -m tests.test_document_repository