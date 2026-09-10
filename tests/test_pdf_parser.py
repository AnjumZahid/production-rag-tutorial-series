from pathlib import Path

from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser


def main() -> None:
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()

    loaded_result = loader.load_directory(
        Path("docs"),
        continue_on_error=True,
    )

    parsed_documents = parser.parse(loaded_result.documents)

    print("\n=== PDF PARSER TEST ===")
    print("Loaded PDFs:", len(loaded_result.loaded_sources))
    print("Parsed pages:", len(parsed_documents))
    print(
        "Empty pages:",
        sum(document.metadata["is_empty"] for document in parsed_documents),
    )

    first_page = parsed_documents[0]

    print("\n=== FIRST PAGE METADATA ===")
    print(first_page.metadata)

    print("\n=== FIRST PAGE PARSED TEXT ===")
    print(first_page.page_content[:1500])


if __name__ == "__main__":
    main()


# uv run python -m tests.test_pdf_parser
