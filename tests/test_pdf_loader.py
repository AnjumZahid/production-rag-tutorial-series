from pathlib import Path

from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader


def main() -> None:
    loader = PDFDocumentLoader()

    result = loader.load_directory(
        Path("docs"),
        continue_on_error=True,
    )

    print("\n=== PDF LOADING SUMMARY ===")
    print("PDFs loaded:", len(result.loaded_sources))
    print("Pages loaded:", len(result.documents))
    print("Failures:", len(result.failures))

    if result.failures:
        print("\n=== FAILED FILES ===")
        for failure in result.failures:
            print(failure)

    if not result.documents:
        print("\nNo PDF pages were loaded.")
        return

    first_page = result.documents[5]

    print("\n=== FIRST PAGE METADATA ===")
    print(first_page.metadata)

    print("\n=== FIRST PAGE TEXT ===")
    print("PAGE:", first_page.metadata.get("page_number"))
    print("FILE:", first_page.metadata.get("filename"))
    print("-" * 80)
    print(first_page.page_content)


if __name__ == "__main__":
    main()


# uv run python -m tests.test_pdf_loader