# installation
# uv add langchain-community pypdf

from collections.abc import Iterable
from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from backend.app.core.exceptions import (
    AppError,
    DocumentNotFoundError,
    DocumentParsingError,
    UnsupportedDocumentTypeError,
)
from backend.app.core.logging import get_logger
from backend.app.ingestion.loaders.base import BaseDocumentLoader


logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class PDFLoadFailure:
    source: str
    code: str
    message: str


@dataclass(slots=True)
class PDFBatchLoadResult:
    documents: list[Document] = field(default_factory=list)
    loaded_sources: list[str] = field(default_factory=list)
    failures: list[PDFLoadFailure] = field(default_factory=list)


class PDFDocumentLoader(BaseDocumentLoader):
    """Load one or multiple PDFs as page-wise LangChain Documents."""

    def load(self, source: Path) -> list[Document]:
        """Load one PDF file."""

        source = source.expanduser().resolve()

        if not source.exists() or not source.is_file():
            raise DocumentNotFoundError(details={"path": str(source)})

        if source.suffix.lower() != ".pdf":
            raise UnsupportedDocumentTypeError(
                details={
                    "path": str(source),
                    "extension": source.suffix,
                }
            )

        logger.info("pdf_loading_started", filename=source.name)

        try:
            file_hash = self._calculate_sha256(source)
            documents = PyPDFLoader(str(source)).load()

            if not documents:
                raise DocumentParsingError(
                    message="No pages could be extracted from the PDF.",
                    details={"path": str(source)},
                )

        except AppError:
            raise

        except Exception as exc:
            raise DocumentParsingError(
                details={
                    "path": str(source),
                    "error_type": type(exc).__name__,
                }
            ) from exc

        total_pages = len(documents)

        for page_index, document in enumerate(documents):
            original_page_index = document.metadata.get("page", page_index)
            page_number = (
                original_page_index + 1
                if isinstance(original_page_index, int)
                else page_index + 1
            )

            document.metadata.update(
                {
                    "document_id": file_hash,
                    "page_id": f"{file_hash}:{page_number}",
                    "source": str(source),
                    "filename": source.name,
                    "file_type": "pdf",
                    "file_hash": file_hash,
                    "file_size_bytes": source.stat().st_size,
                    "page_number": page_number,
                    "total_pages": total_pages,
                }
            )

        logger.info(
            "pdf_loading_completed",
            filename=source.name,
            document_id=file_hash,
            page_count=total_pages,
        )

        return documents

    def load_many(
        self,
        sources: Iterable[Path],
        *,
        continue_on_error: bool = False,
    ) -> PDFBatchLoadResult:
        """Load multiple PDF files and combine their page documents."""

        unique_sources = sorted(
            {
                Path(source).expanduser().resolve()
                for source in sources
            },
            key=lambda path: str(path).lower(),
        )

        if not unique_sources:
            raise DocumentNotFoundError(
                message="No PDF files were provided."
            )

        result = PDFBatchLoadResult()

        for source in unique_sources:
            try:
                documents = self.load(source)

                result.documents.extend(documents)
                result.loaded_sources.append(str(source))

            except AppError as exc:
                logger.error(
                    "pdf_loading_failed",
                    source=str(source),
                    error_code=exc.code,
                    error_message=exc.message,
                )

                result.failures.append(
                    PDFLoadFailure(
                        source=str(source),
                        code=exc.code,
                        message=exc.message,
                    )
                )

                if not continue_on_error:
                    raise

        logger.info(
            "pdf_batch_loading_completed",
            loaded_file_count=len(result.loaded_sources),
            failed_file_count=len(result.failures),
            total_page_count=len(result.documents),
        )

        return result

    def load_directory(
        self,
        directory: Path,
        *,
        recursive: bool = False,
        continue_on_error: bool = False,
    ) -> PDFBatchLoadResult:
        """Load all PDF files from a directory."""

        directory = directory.expanduser().resolve()

        if not directory.exists() or not directory.is_dir():
            raise DocumentNotFoundError(
                message="The PDF directory was not found.",
                details={"path": str(directory)},
            )

        pattern = "**/*.pdf" if recursive else "*.pdf"
        pdf_files = list(directory.glob(pattern))

        if not pdf_files:
            raise DocumentNotFoundError(
                message="No PDF files were found in the directory.",
                details={"path": str(directory)},
            )

        return self.load_many(
            pdf_files,
            continue_on_error=continue_on_error,
        )

    @staticmethod
    def _calculate_sha256(source: Path) -> str:
        """Generate a stable unique hash for a PDF file."""

        digest = sha256()

        with source.open("rb") as file:
            while chunk := file.read(1024 * 1024):
                digest.update(chunk)

        return digest.hexdigest()
    
    # uv run python -c "from pathlib import Path; from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader; result = PDFDocumentLoader().load_directory(Path('docs'), continue_on_error=True); print('PDFs loaded:', len(result.loaded_sources)); print('Pages loaded:', len(result.documents)); print('Failures:', len(result.failures)); print(result.documents[0].metadata if result.documents else 'No pages loaded')"