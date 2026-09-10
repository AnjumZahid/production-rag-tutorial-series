import asyncio
import inspect
from pathlib import Path
from uuid import uuid4

from backend.app.database.repositories import DocumentRepository
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.embeddings.factory import get_embedding_provider
from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser
from backend.app.ingestion.processors.chunker import DocumentChunker
from backend.app.ingestion.processors.text_cleaner import TextCleaner
from backend.app.services import DocumentIngestionService
from backend.app.vectorstores.factory import get_vector_store


PDF_PATH = Path("docs/who_pen_guidelines.pdf")
QUERY = "What treatment is recommended for high blood pressure?"


def get_public_value(
    obj: object,
    attribute_name: str,
    default: str,
) -> str:
    value = getattr(obj, attribute_name, None)

    if value is None:
        return default

    if callable(value):
        value = value()

    return str(value)


def run_similarity_search(
    vector_store: object,
    query: str,
    k: int,
):
    similarity_search = getattr(vector_store, "similarity_search")

    try:
        return similarity_search(
            query=query,
            k=k,
        )
    except TypeError:
        try:
            return similarity_search(
                query,
                k,
            )
        except TypeError:
            return similarity_search(
                query=query,
                top_k=k,
            )


async def close_resource(resource: object | None) -> None:
    if resource is None:
        return

    close_method = getattr(resource, "close", None)

    if close_method is None or not callable(close_method):
        return

    result = close_method()

    if inspect.isawaitable(result):
        await result


async def main() -> None:
    if not PDF_PATH.exists():
        raise FileNotFoundError(
            f"Test PDF was not found: {PDF_PATH}"
        )

    unique_value = uuid4().hex

    organization_id = f"real-org-{unique_value[:8]}"
    user_id = f"real-user-{unique_value[8:16]}"
    knowledge_base_id = f"real-kb-{unique_value[16:24]}"

    embedding_provider = get_embedding_provider()

    embedding_provider_name = get_public_value(
        embedding_provider,
        "provider_name",
        "huggingface",
    )

    embedding_model_name = get_public_value(
        embedding_provider,
        "model_name",
        "sentence-transformers/all-MiniLM-L6-v2",
    )

    vector_store = None
    session_factory = get_session_factory()

    created_document_id: str | None = None
    stored_vector_ids: tuple[str, ...] = ()

    try:
        vector_store = get_vector_store(
            embedding_provider=embedding_provider,
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )

        async with session_factory() as session:
            repository = DocumentRepository(session)

            service = DocumentIngestionService(
                session=session,
                repository=repository,
                loader=PDFDocumentLoader(),
                parser=PDFDocumentParser(),
                cleaner=TextCleaner(),
                chunker=DocumentChunker(),
                vector_store=vector_store,
                embedding_provider_name=embedding_provider_name,
                embedding_model_name=embedding_model_name,
                embedding_dimension=384,
                vector_store_provider_name="chroma",
            )

            try:
                result = await service.ingest_pdf(
                    file_path=PDF_PATH,
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                )

                created_document_id = result.document_id
                stored_vector_ids = result.vector_ids

                assert result.status == "completed"
                assert result.total_pages == 85
                assert result.chunk_count > 0
                assert len(result.vector_ids) == result.chunk_count

                stored_document = await repository.get_by_id(
                    document_id=result.document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert stored_document is not None
                assert stored_document.status == "completed"
                assert stored_document.total_pages == result.total_pages
                assert stored_document.chunk_count == result.chunk_count
                assert stored_document.embedding_dimension == 384

                retrieved_documents = await asyncio.to_thread(
                    run_similarity_search,
                    vector_store,
                    QUERY,
                    3,
                )

                assert len(retrieved_documents) == 3

                for document in retrieved_documents:
                    metadata = document.metadata

                    assert metadata["organization_id"] == organization_id
                    assert metadata["user_id"] == user_id
                    assert metadata["knowledge_base_id"] == knowledge_base_id

                print("\n=== REAL DOCUMENT INGESTION TEST ===")
                print("Document ID:", result.document_id)
                print("Status:", result.status)
                print("Pages:", result.total_pages)
                print("Chunks:", result.chunk_count)
                print("Vectors:", len(result.vector_ids))
                print("Retrieved documents:", len(retrieved_documents))

                print("\nTop result preview:")
                print(
                    retrieved_documents[0].page_content[:500]
                )

                await asyncio.to_thread(
                    vector_store.delete_chunks,
                    list(stored_vector_ids),
                )

                print("\nReal Chroma vectors deleted.")

                stored_vector_ids = ()

                deleted = await repository.delete_document_record(
                    document_id=result.document_id,
                    organization_id=organization_id,
                    user_id=user_id,
                )

                assert deleted is True

                await session.commit()

                created_document_id = None

                print("Temporary MySQL record deleted.")
                print(
                    "Real document ingestion test passed successfully."
                )

            finally:
                if stored_vector_ids:
                    await asyncio.to_thread(
                        vector_store.delete_chunks,
                        list(stored_vector_ids),
                    )

                    print("Cleanup: remaining Chroma vectors deleted.")

                if created_document_id is not None:
                    deleted = await repository.delete_document_record(
                        document_id=created_document_id,
                        organization_id=organization_id,
                        user_id=user_id,
                    )

                    if deleted:
                        await session.commit()
                        print("Cleanup: remaining MySQL record deleted.")

    finally:
        await close_resource(vector_store)
        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())


# uv run python -m tests.test_real_document_ingestion