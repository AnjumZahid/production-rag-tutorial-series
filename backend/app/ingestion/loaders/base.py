# installations
# uv add langchain-core

from abc import ABC, abstractmethod
from pathlib import Path

from langchain_core.documents import Document


class BaseDocumentLoader(ABC):
    """Common interface for all document loaders."""

    @abstractmethod
    def load(self, source: Path) -> list[Document]:
        """Load a source and return LangChain Document objects."""
        raise NotImplementedError
    
# uv run python -c "from backend.app.ingestion.loaders.base import BaseDocumentLoader; print('BaseDocumentLoader imported successfully')"