from pathlib import Path

from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader
from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser
from backend.app.ingestion.processors.text_cleaner import TextCleaner


def main() -> None:
    loader = PDFDocumentLoader()
    parser = PDFDocumentParser()
    cleaner = TextCleaner()

    loaded = loader.load_directory(
        Path("docs"),
        continue_on_error=True,
    )

    parsed = parser.parse(loaded.documents)
    cleaned = cleaner.clean(parsed)

    print("\n=== TEXT CLEANER TEST ===")
    print("Parsed pages:", len(parsed))
    print("Cleaned pages:", len(cleaned))

    first_page = cleaned[0]

    print("\n=== FIRST PAGE METADATA ===")
    print(first_page.metadata)

    print("\n=== FIRST PAGE CLEANED TEXT ===")
    print(first_page.page_content[:1500])


if __name__ == "__main__":
    main()



# uv run python -m tests.test_text_cleaner