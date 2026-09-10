from collections import defaultdict
from hashlib import sha256

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from backend.app.core.config import settings
from backend.app.core.exceptions import DocumentChunkingError
from backend.app.core.logging import get_logger


logger = get_logger(__name__)


class DocumentChunker:
    """Split cleaned documents into smaller overlapping chunks."""

    def __init__(
        self,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ) -> None:
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = (
            settings.chunk_overlap
            if chunk_overlap is None
            else chunk_overlap
        )

        if self.chunk_size <= 0:
            raise DocumentChunkingError(
                message="Chunk size must be greater than zero."
            )

        if self.chunk_overlap < 0:
            raise DocumentChunkingError(
                message="Chunk overlap cannot be negative."
            )

        if self.chunk_overlap >= self.chunk_size:
            raise DocumentChunkingError(
                message="Chunk overlap must be smaller than chunk size."
            )

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
            add_start_index=True,
            strip_whitespace=True,
        )

    def split(self, documents: list[Document]) -> list[Document]:
        if not documents:
            raise DocumentChunkingError(
                message="No cleaned documents were provided for chunking."
            )

        for position, document in enumerate(documents, start=1):
            if not isinstance(document, Document):
                raise DocumentChunkingError(
                    message="An invalid document object was provided.",
                    details={"position": position},
                )

        logger.info(
            "document_chunking_started",
            document_count=len(documents),
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

        try:
            chunks = self._splitter.split_documents(documents)
        except Exception as exc:
            raise DocumentChunkingError(
                details={"error_type": type(exc).__name__}
            ) from exc

        if not chunks:
            raise DocumentChunkingError(
                message="No chunks were created from the documents."
            )

        page_chunk_indexes: dict[str, int] = defaultdict(int)

        for chunk in chunks:
            source_key = str(
                chunk.metadata.get("page_id")
                or chunk.metadata.get("document_id")
                or chunk.metadata.get("source")
                or "unknown"
            )

            page_chunk_indexes[source_key] += 1
            chunk_index = page_chunk_indexes[source_key]

            chunk_hash = sha256(
                (
                    f"{source_key}:{chunk_index}:"
                    f"{chunk.page_content}"
                ).encode("utf-8")
            ).hexdigest()

            chunk.metadata.update(
                {
                    "chunk_id": chunk_hash,
                    "chunk_index": chunk_index,
                    "chunk_length": len(chunk.page_content),
                    "configured_chunk_size": self.chunk_size,
                    "configured_chunk_overlap": self.chunk_overlap,
                }
            )

        logger.info(
            "document_chunking_completed",
            input_document_count=len(documents),
            chunk_count=len(chunks),
        )

        return chunks
    
# uv run python -c "from pathlib import Path; from backend.app.ingestion.loaders.pdf_loader import PDFDocumentLoader; from backend.app.ingestion.parsers.pdf_parser import PDFDocumentParser; from backend.app.ingestion.processors.text_cleaner import TextCleaner; from backend.app.ingestion.processors.chunker import DocumentChunker; loaded=PDFDocumentLoader().load_directory(Path('docs')); parsed=PDFDocumentParser().parse(loaded.documents); cleaned=TextCleaner().clean(parsed); chunks=DocumentChunker().split(cleaned); print('Cleaned pages:', len(cleaned)); print('Chunks:', len(chunks)); print(chunks[0].metadata); print('-'*80); print(chunks[0].page_content)"