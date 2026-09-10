from pathlib import Path

from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser
from backend.app.ingestion.processors.chunker import DocumentChunker
from backend.app.ingestion.processors.text_cleaner import TextCleaner


def main() -> None:
    loaded = PDFDocumentLoader().load_directory(
        Path("docs"),
        continue_on_error=True,
    )

    parsed = PDFDocumentParser().parse(loaded.documents)
    cleaned = TextCleaner().clean(parsed)
    chunks = DocumentChunker().split(cleaned)

    print("\n=== DOCUMENT CHUNKER TEST ===")
    print("PDFs loaded:", len(loaded.loaded_sources))
    print("Cleaned pages:", len(cleaned))
    print("Chunks created:", len(chunks))

    first_chunk = chunks[0]

    print("\n=== FIRST CHUNK METADATA ===")
    print(first_chunk.metadata)

    print("\n=== FIRST CHUNK TEXT ===")
    print(first_chunk.page_content)

    print("\n=== FIRST 5 CHUNKS SUMMARY ===")
    for chunk in chunks[:5]:
        print(
            "File:",
            chunk.metadata.get("filename"),
            "| Page:",
            chunk.metadata.get("page_number"),
            "| Chunk:",
            chunk.metadata.get("chunk_index"),
            "| Length:",
            chunk.metadata.get("chunk_length"),
        )


if __name__ == "__main__":
    main()

# uv run python -m tests.test_chunker