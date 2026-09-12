from langchain_core.documents import Document

from backend.app.core.exceptions import DocumentParsingError
from backend.app.core.logging import get_logger
from backend.app.ingestion.parsers.base import BaseDocumentParser


logger = get_logger(__name__)


class PDFDocumentParser(BaseDocumentParser):
    """Normalize loaded PDF pages and validate extracted text."""

    def parse(self, documents: list[Document]) -> list[Document]:
        if not documents:
            raise DocumentParsingError(
                message="No loaded PDF pages were provided."
            )

        logger.info(
            "pdf_parsing_started",
            page_count=len(documents),
        )

        parsed_documents: list[Document] = []
        empty_page_count = 0

        for position, document in enumerate(documents, start=1):
            if not isinstance(document, Document):
                raise DocumentParsingError(
                    message="An invalid document object was provided.",
                    details={"position": position},
                )

            text = document.page_content or ""

            # Basic structural normalization only.
            text = (
                text.replace("\x00", "")
                .replace("\r\n", "\n")
                .replace("\r", "\n")
                .strip()
            )

            is_empty = not bool(text)

            if is_empty:
                empty_page_count += 1

            metadata = dict(document.metadata)
            metadata.update(
                {
                    "parser": "pypdf",
                    "content_length": len(text),
                    "is_empty": is_empty,
                }
            )

            parsed_documents.append(
                Document(
                    page_content=text,
                    metadata=metadata,
                )
            )

        if empty_page_count == len(parsed_documents):
            raise DocumentParsingError(
                message=(
                    "No extractable text was found. "
                    "The PDF may be scanned and require OCR."
                ),
                details={
                    "page_count": len(parsed_documents),
                    "empty_page_count": empty_page_count,
                },
            )

        logger.info(
            "pdf_parsing_completed",
            page_count=len(parsed_documents),
            empty_page_count=empty_page_count,
        )

        return parsed_documents
    

# uv run python -c "from pathlib import Path; from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader; from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser; loaded = PDFDocumentLoader().load_directory(Path('docs')); parsed = PDFDocumentParser().parse(loaded.documents); print('Parsed pages:', len(parsed)); print('Empty pages:', sum(d.metadata['is_empty'] for d in parsed)); print('First page length:', parsed[0].metadata['content_length']); print(parsed[0].page_content[:1000])"
