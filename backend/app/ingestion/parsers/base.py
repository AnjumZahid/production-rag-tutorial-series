from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseDocumentParser(ABC):
    """Common interface for document parsers."""

    @abstractmethod
    def parse(self, documents: list[Document]) -> list[Document]:
        """Parse loaded documents and return normalized documents."""
        raise NotImplementedError
    
# uv run python -c "from backend.app.ingestion.parsers.base import BaseDocumentParser; print('BaseDocumentParser imported successfully')"