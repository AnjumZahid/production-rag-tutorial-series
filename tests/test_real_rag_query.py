import asyncio
from pathlib import Path
from uuid import uuid4

from backend.app.core.config import settings
from backend.app.core.exceptions import AppError
from backend.app.database.repositories import DocumentRepository
from backend.app.database.session import (
    close_database_connection,
    get_session_factory,
)
from backend.app.embeddings.factory import (
    get_embedding_provider,
)
from backend.app.generation import GroundedAnswerService
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
from backend.app.llms import get_llm_provider
from backend.app.retrieval import RetrievalService
from backend.app.services.document_ingestion import (
    DocumentIngestionService,
)
from backend.app.services.rag_query import RAGQueryService
from backend.app.vectorstores.factory import get_vector_store


async def main() -> None:
    pdf_path = Path(
        "docs/who_pen_guidelines.pdf"
    ).resolve()

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"Test PDF was not found: {pdf_path}"
        )

    unique_value = uuid4().hex

    organization_id = (
        f"real-rag-org-{unique_value[:8]}"
    )
    user_id = (
        f"real-rag-user-{unique_value[8:16]}"
    )
    knowledge_base_id = (
        f"real-rag-kb-{unique_value[16:24]}"
    )

    session_factory = get_session_factory()

    vector_store = None
    llm_provider = None
    ingestion_result = None
    vectors_deleted = False
    database_record_deleted = False

    try:
        embedding_provider = get_embedding_provider()

        vector_store = get_vector_store(
            embedding_provider=embedding_provider,
            organization_id=organization_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
        )

        llm_provider = get_llm_provider()

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

        async with session_factory() as session:
            repository = DocumentRepository(session)

            ingestion_service = DocumentIngestionService(
                session=session,
                repository=repository,
                loader=PDFDocumentLoader(),
                parser=PDFDocumentParser(),
                cleaner=TextCleaner(),
                chunker=DocumentChunker(),
                vector_store=vector_store,
                embedding_provider_name=(
                    type(embedding_provider).__name__
                ),
                embedding_model_name=embedding_model_name,
                embedding_dimension=384,
                vector_store_provider_name=(
                    type(vector_store).__name__
                ),
            )

            print(
                "\nIngesting real PDF for the RAG test:",
                pdf_path.name,
            )

            ingestion_result = (
                await ingestion_service.ingest_pdf(
                    file_path=pdf_path,
                    organization_id=organization_id,
                    user_id=user_id,
                    knowledge_base_id=knowledge_base_id,
                )
            )

            assert ingestion_result.status == "completed"
            assert ingestion_result.chunk_count > 0
            assert ingestion_result.vector_ids

            retrieval_service = RetrievalService(
                vector_store=vector_store,
                default_k=settings.retrieval_top_k,
                max_k=20,
            )

            generation_service = GroundedAnswerService(
                llm_provider=llm_provider,
                max_context_characters=24_000,
            )

            rag_service = RAGQueryService(
                retrieval_service=retrieval_service,
                generation_service=generation_service,
            )

            question = (
                "According to the document, what lifestyle "
                "interventions are recommended for managing "
                "high blood pressure?"
            )

            result = await rag_service.answer(
                query=question,
                k=5,
                document_id=ingestion_result.document_id,
            )

            assert result.query == question
            assert result.answer.strip()
            assert result.grounded is True
            assert result.citations
            assert result.sources
            assert result.retrieved_chunk_count > 0

            source_citation_ids = {
                source.citation_id
                for source in result.sources
            }

            assert set(result.citations).issubset(
                source_citation_ids
            )

            for source in result.sources:
                assert (
                    source.document_id
                    == ingestion_result.document_id
                )

                assert (
                    source.metadata.get("organization_id")
                    == organization_id
                )

                assert (
                    source.metadata.get("user_id")
                    == user_id
                )

                assert (
                    source.metadata.get(
                        "knowledge_base_id"
                    )
                    == knowledge_base_id
                )

            print("\n=== REAL END-TO-END RAG TEST ===")
            print(
                "Document ID:",
                ingestion_result.document_id,
            )
            print(
                "Pages:",
                ingestion_result.total_pages,
            )
            print(
                "Indexed chunks:",
                ingestion_result.chunk_count,
            )
            print(
                "Retrieved chunks:",
                result.retrieved_chunk_count,
            )
            print("Grounded:", result.grounded)
            print("Citations:", result.citations)
            print("\nQuestion:")
            print(result.query)
            print("\nGemini answer:")
            print(result.answer)
            print("\nValidated sources:")

            for source in result.sources:
                print(
                    f"[{source.citation_id}] "
                    f"file={source.filename} "
                    f"page={source.page_number} "
                    f"chunk_id={source.chunk_id}"
                )

            # Delete vectors before deleting their MySQL references.
            await asyncio.to_thread(
                vector_store.delete_chunks,
                list(ingestion_result.vector_ids),
            )

            vectors_deleted = True

            deleted = (
                await repository.delete_document_record(
                    document_id=(
                        ingestion_result.document_id
                    ),
                    organization_id=organization_id,
                    user_id=user_id,
                )
            )

            assert deleted is True

            await session.commit()

            database_record_deleted = True

            print("\nReal Chroma vectors deleted.")
            print("Temporary MySQL record deleted.")
            print(
                "Real end-to-end RAG test "
                "passed successfully."
            )

    finally:
        if (
            ingestion_result is not None
            and vector_store is not None
            and not vectors_deleted
        ):
            try:
                await asyncio.to_thread(
                    vector_store.delete_chunks,
                    list(ingestion_result.vector_ids),
                )
            except Exception as cleanup_error:
                print(
                    "Vector cleanup warning:",
                    type(cleanup_error).__name__,
                    str(cleanup_error),
                )

        if not database_record_deleted:
            try:
                async with session_factory() as cleanup_session:
                    cleanup_repository = DocumentRepository(
                        cleanup_session
                    )

                    test_documents = (
                        await cleanup_repository.list_documents(
                            organization_id=organization_id,
                            user_id=user_id,
                            knowledge_base_id=knowledge_base_id,
                        )
                    )

                    for document in test_documents:
                        await cleanup_repository.delete_document_record(
                            document_id=document.id,
                            organization_id=organization_id,
                            user_id=user_id,
                        )

                    await cleanup_session.commit()

            except Exception as cleanup_error:
                print(
                    "Database cleanup warning:",
                    type(cleanup_error).__name__,
                    str(cleanup_error),
                )

        if vector_store is not None:
            try:
                await asyncio.to_thread(
                    vector_store.close,
                )
            except Exception as close_error:
                print(
                    "Vector-store close warning:",
                    type(close_error).__name__,
                    str(close_error),
                )

        if llm_provider is not None:
            try:
                close_method = getattr(
                    llm_provider,
                    "close",
                    None,
                )

                if callable(close_method):
                    close_method()

            except Exception as close_error:
                print(
                    "LLM-provider close warning:",
                    type(close_error).__name__,
                    str(close_error),
                )

        await close_database_connection()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except AppError as exc:
        print("\nReal end-to-end RAG test failed safely.")
        print("Code:", exc.code)
        print("Message:", exc.message)

        if exc.details:
            safe_details = dict(exc.details)
            safe_details.pop("api_key", None)
            safe_details.pop("authorization", None)
            safe_details.pop("headers", None)

            print("Details:", safe_details)

        raise SystemExit(1)

# uv run python -m tests.test_real_rag_query