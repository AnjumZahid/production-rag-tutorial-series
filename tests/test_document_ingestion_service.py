import asyncio
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from langchain_core.documents import Document

from backend.app.core.exceptions import DuplicateDocumentError
from backend.app.database.repositories import DocumentRepository
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.services import DocumentIngestionService


class FakeLoader:
    def load(self, path: Path) -> list[Document]:
        return [
            Document(
                page_content="First test page.",
                metadata={
                    "source": str(path),
                    "page_number": 1,
                },
            )
        ]


class FakeParser:
    def parse(
        self,
        documents: list[Document],
    ) -> list[Document]:
        return list(documents)


class FakeCleaner:
    def clean(
        self,
        documents: list[Document],
    ) -> list[Document]:
        return list(documents)


class FakeChunker:
    def split(
        self,
        documents: list[Document],
    ) -> list[Document]:
        source = documents[0].metadata["source"]

        return [
            Document(
                page_content="First test chunk.",
                metadata={
                    "source": source,
                    "page_number": 1,
                    "chunk_index": 0,
                    "chunk_id": sha256(
                        b"first-test-chunk"
                    ).hexdigest(),
                },
            ),
            Document(
                page_content="Second test chunk.",
                metadata={
                    "source": source,
                    "page_number": 1,
                    "chunk_index": 1,
                    "chunk_id": sha256(
                        b"second-test-chunk"
                    ).hexdigest(),
                },
            ),
        ]


class FakeEmbeddingProvider:
    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        return [
            [float(index), 0.25, 0.75]
            for index, _ in enumerate(texts)
        ]


class FakeVectorStore:
    def __init__(self) -> None:
        self.stored_ids: list[str] = []

    def add_documents(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> list[str]:
        assert len(documents) == len(embeddings)

        self.stored_ids = [
            sha256(
                (
                    f"{document.metadata['organization_id']}:"
                    f"{document.metadata['user_id']}:"
                    f"{document.metadata['knowledge_base_id']}:"
                    f"{document.metadata['chunk_id']}"
                ).encode("utf-8")
            ).hexdigest()
            for document in documents
        ]

        return list(self.stored_ids)

    def delete_documents(
        self,
        vector_ids: list[str],
    ) -> None:
        ids_to_delete = set(vector_ids)

        self.stored_ids = [
            vector_id
            for vector_id in self.stored_ids
            if vector_id not in ids_to_delete
        ]


async def main() -> None:
    unique_value = uuid4().hex

    organization_id = f"test-org-{unique_value[:8]}"
    user_id = f"test-user-{unique_value[8:16]}"
    knowledge_base_id = f"test-kb-{unique_value[16:24]}"

    session_factory = get_session_factory()
    vector_store = FakeVectorStore()

    created_document_id: str | None = None

    try:
        with TemporaryDirectory() as temporary_directory:
            pdf_path = (
                Path(temporary_directory)
                / "temporary_ingestion_test.pdf"
            )

            pdf_path.write_bytes(
                b"temporary fake PDF content for service testing"
            )

            async with session_factory() as session:
                repository = DocumentRepository(session)

                service = DocumentIngestionService(
                    session=session,
                    repository=repository,
                    loader=FakeLoader(),
                    parser=FakeParser(),
                    cleaner=FakeCleaner(),
                    chunker=FakeChunker(),
                    embedding_provider=FakeEmbeddingProvider(),
                    vector_store=vector_store,
                    embedding_provider_name="fake",
                    embedding_model_name="fake-test-model",
                    vector_store_provider_name="fake-vector-store",
                )

                result = await service.ingest_pdf(
                    file_path=pdf_path,
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                )

                created_document_id = result.document_id

                assert result.status == "completed"
                assert result.total_pages == 1
                assert result.chunk_count == 2
                assert len(result.vector_ids) == 2

                stored_document = await repository.get_by_id(
                    document_id=result.document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert stored_document is not None
                assert stored_document.status == "completed"
                assert stored_document.chunk_count == 2
                assert stored_document.embedding_dimension == 3

                duplicate_detected = False

                try:
                    await service.ingest_pdf(
                        file_path=pdf_path,
                        organization_id=organization_id,
                        user_id=user_id,
                        knowledge_base_id=knowledge_base_id,
                    )
                except DuplicateDocumentError:
                    duplicate_detected = True

                assert duplicate_detected is True

                print(
                    "\n=== DOCUMENT INGESTION SERVICE TEST ==="
                )
                print("Document ID:", result.document_id)
                print("Status:", result.status)
                print("Pages:", result.total_pages)
                print("Chunks:", result.chunk_count)
                print("Vectors:", len(result.vector_ids))
                print("Duplicate protection confirmed.")

                deleted = await repository.delete_document_record(
                    document_id=result.document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert deleted is True

                await session.commit()

                vector_store.delete_documents(
                    list(result.vector_ids)
                )

                assert vector_store.stored_ids == []

                created_document_id = None

                print("Temporary database record deleted.")
                print(
                    "Document ingestion service test "
                    "passed successfully."
                )

    finally:
        if created_document_id is not None:
            async with session_factory() as cleanup_session:
                cleanup_repository = DocumentRepository(
                    cleanup_session
                )

                existing_document = (
                    await cleanup_repository.get_by_id(
                        document_id=created_document_id,
                        organization_id=organization_id,
                        user_id=user_id,
                    )
                )

                if existing_document is not None:
                    await cleanup_repository.delete_document_record(
                        document_id=created_document_id,
                        organization_id=organization_id,
                        user_id=user_id,
                    )
                    await cleanup_session.commit()

        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())


# uv run python -m tests.test_document_ingestion_service