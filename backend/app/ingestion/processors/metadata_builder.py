from datetime import UTC, datetime
from uuid import uuid4

from langchain_core.documents import Document

from backend.app.core.exceptions import DocumentMetadataError
from backend.app.core.logging import get_logger


logger = get_logger(__name__)


class MetadataBuilder:
    """Validate and enrich chunk metadata before embedding and storage."""

    def build(
        self,
        chunks: list[Document],
        *,
        user_id: str | None = None,
        collection_id: str | None = None,
    ) -> list[Document]:
        if not chunks:
            raise DocumentMetadataError(
                message="No chunks were provided for metadata building."
            )

        ingestion_id = str(uuid4())
        ingested_at = datetime.now(UTC).isoformat()

        prepared_chunks: list[Document] = []

        logger.info(
            "metadata_building_started",
            chunk_count=len(chunks),
            ingestion_id=ingestion_id,
        )

        for global_index, chunk in enumerate(chunks, start=1):
            if not isinstance(chunk, Document):
                raise DocumentMetadataError(
                    message="An invalid chunk object was provided.",
                    details={"position": global_index},
                )

            required_fields = (
                "document_id",
                "chunk_id",
                "filename",
                "page_number",
            )

            missing_fields = [
                field
                for field in required_fields
                if field not in chunk.metadata
            ]

            if missing_fields:
                raise DocumentMetadataError(
                    message="Required chunk metadata is missing.",
                    details={
                        "position": global_index,
                        "missing_fields": missing_fields,
                    },
                )

            metadata = dict(chunk.metadata)

            metadata.update(
                {
                    "ingestion_id": ingestion_id,
                    "ingested_at": ingested_at,
                    "metadata_schema_version": "1.0",
                    "global_chunk_index": global_index,
                }
            )

            if user_id is not None:
                metadata["user_id"] = user_id

            if collection_id is not None:
                metadata["collection_id"] = collection_id

            prepared_chunks.append(
                Document(
                    page_content=chunk.page_content,
                    metadata=metadata,
                )
            )

        logger.info(
            "metadata_building_completed",
            chunk_count=len(prepared_chunks),
            ingestion_id=ingestion_id,
        )

        return prepared_chunks