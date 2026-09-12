import re

from langchain_core.documents import Document

from backend.app.core.exceptions import DocumentParsingError
from backend.app.core.logging import get_logger


logger = get_logger(__name__)


class TextCleaner:
    """Clean parsed document text while preserving metadata."""

    def clean(
        self,
        documents: list[Document],
        *,
        drop_empty: bool = True,
    ) -> list[Document]:
        if not documents:
            raise DocumentParsingError(
                message="No parsed documents were provided for cleaning."
            )

        logger.info(
            "text_cleaning_started",
            document_count=len(documents),
        )

        cleaned_documents: list[Document] = []
        removed_empty_count = 0

        for position, document in enumerate(documents, start=1):
            if not isinstance(document, Document):
                raise DocumentParsingError(
                    message="An invalid document object was provided.",
                    details={"position": position},
                )

            original_text = document.page_content or ""
            cleaned_text = self._clean_text(original_text)

            if not cleaned_text and drop_empty:
                removed_empty_count += 1
                continue

            metadata = dict(document.metadata)
            metadata.update(
                {
                    "original_content_length": len(original_text),
                    "cleaned_content_length": len(cleaned_text),
                    "text_cleaned": True,
                }
            )

            cleaned_documents.append(
                Document(
                    page_content=cleaned_text,
                    metadata=metadata,
                )
            )

        if not cleaned_documents:
            raise DocumentParsingError(
                message="No usable text remained after cleaning."
            )

        logger.info(
            "text_cleaning_completed",
            input_count=len(documents),
            output_count=len(cleaned_documents),
            removed_empty_count=removed_empty_count,
        )

        return cleaned_documents

    @staticmethod
    def _clean_text(text: str) -> str:
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()
    
# uv run python -c "from pathlib import Path; from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader; from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser; from backend.app.ingestion.processors.text_cleaner import TextCleaner; loaded = PDFDocumentLoader().load_directory(Path('docs'), continue_on_error=True); parsed = PDFDocumentParser().parse(loaded.documents); cleaned = TextCleaner().clean(parsed); print('Cleaned pages:', len(cleaned)); print(cleaned[0].metadata); print('-' * 80); print(cleaned[0].page_content[:1500])"