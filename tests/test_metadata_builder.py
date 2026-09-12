from pathlib import Path

from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser
from backend.app.ingestion.processors.chunker import DocumentChunker
from backend.app.ingestion.processors.metadata_builder import MetadataBuilder
from backend.app.ingestion.processors.text_cleaner import TextCleaner


def main() -> None:
    loaded = PDFDocumentLoader().load_directory(Path("docs"))
    parsed = PDFDocumentParser().parse(loaded.documents)
    cleaned = TextCleaner().clean(parsed)
    chunks = DocumentChunker().split(cleaned)

    prepared_chunks = MetadataBuilder().build(
        chunks,
        user_id="test-user-001",
        collection_id="who-guidelines",
    )

    print("Prepared chunks:", len(prepared_chunks))
    print("\nFirst chunk metadata:")
    print(prepared_chunks[0].metadata)
    print("\nFirst chunk text:")
    print(prepared_chunks[0].page_content[:1000])


if __name__ == "__main__":
    main()


# uv run python -m tests.test_metadata_builder