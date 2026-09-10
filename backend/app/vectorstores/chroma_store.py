# libraries to install
# uv add langchain-chroma

from hashlib import sha256
from pathlib import Path
from typing import Any

import chromadb

from chromadb.config import Settings as ChromaSettings
from chromadb.errors import NotFoundError, UniqueConstraintError
from langchain_chroma import Chroma
from langchain_core.documents import Document

from backend.app.core.config import settings
from backend.app.core.exceptions import VectorStoreError
from backend.app.core.logging import get_logger
from backend.app.embeddings.base import BaseEmbeddingProvider


logger = get_logger(__name__)


class ChromaVectorStore:
    """
    Organization-isolated Chroma vector store.

    Isolation structure:

        Tenant:
            one tenant per organization

        Database:
            one RAG database inside each organization tenant

        Collection:
            one collection per knowledge base

        Metadata filter:
            one user_id per owner

    The backend must obtain organization_id and user_id from trusted
    authentication data, not directly from an unrestricted frontend field.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        *,
        organization_id: str,
        user_id: str,
        knowledge_base_id: str,
        database_name: str | None = None,
        persist_directory: str | None = None,
    ) -> None:
        self.organization_id = self._validate_identifier(
            organization_id,
            field_name="organization_id",
        )

        self.user_id = self._validate_identifier(
            user_id,
            field_name="user_id",
        )

        self.knowledge_base_id = self._validate_identifier(
            knowledge_base_id,
            field_name="knowledge_base_id",
        )

        self.persist_directory = (
            persist_directory
            or settings.chroma_persist_directory
        )

        self.database_name = (
            database_name
            or settings.chroma_database_name
        )

        # Deterministic Chroma-safe names.
        self.tenant_name = self._create_namespace_name(
            prefix="org",
            value=self.organization_id,
        )

        self.collection_name = self._create_namespace_name(
            prefix="kb",
            value=self.knowledge_base_id,
        )

        Path(self.persist_directory).mkdir(
            parents=True,
            exist_ok=True,
        )

        chroma_settings = ChromaSettings(
            is_persistent=True,
            persist_directory=self.persist_directory,
            anonymized_telemetry=False,
        )

        try:
            self._ensure_tenant_and_database(
                chroma_settings=chroma_settings,
            )

            self._client = chromadb.PersistentClient(
                path=self.persist_directory,
                settings=chroma_settings,
                tenant=self.tenant_name,
                database=self.database_name,
            )

            self._store = Chroma(
                client=self._client,
                collection_name=self.collection_name,
                embedding_function=embedding_provider,
            )

        except Exception as exc:
            raise VectorStoreError(
                message=(
                    "The organization-specific Chroma store "
                    "could not be initialized."
                ),
                details={
                    "tenant_name": self.tenant_name,
                    "database_name": self.database_name,
                    "collection_name": self.collection_name,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        logger.info(
            "chroma_store_initialized",
            organization_id=self.organization_id,
            user_id=self.user_id,
            knowledge_base_id=self.knowledge_base_id,
            tenant_name=self.tenant_name,
            database_name=self.database_name,
            collection_name=self.collection_name,
            embedding_provider=embedding_provider.provider_name,
            embedding_model=embedding_provider.model_name,
        )

    def add_documents(
        self,
        documents: list[Document],
    ) -> list[str]:
        """
        Store chunks only inside the current organization, user,
        and knowledge-base namespace.
        """

        if not documents:
            raise VectorStoreError(
                message="No documents were provided for vector storage."
            )

        prepared_documents: list[Document] = []
        document_ids: list[str] = []

        for position, document in enumerate(documents, start=1):
            if not isinstance(document, Document):
                raise VectorStoreError(
                    message="An invalid document object was provided.",
                    details={"position": position},
                )

            if not document.page_content.strip():
                raise VectorStoreError(
                    message="An empty document cannot be stored.",
                    details={"position": position},
                )

            chunk_id = document.metadata.get("chunk_id")

            if not chunk_id:
                raise VectorStoreError(
                    message="A document is missing its chunk_id.",
                    details={"position": position},
                )

            metadata = dict(document.metadata)

            # Reject chunks that already contain conflicting ownership.
            self._validate_existing_ownership(
                metadata=metadata,
                position=position,
            )

            # Always enforce trusted ownership values.
            metadata.update(
                {
                    "organization_id": self.organization_id,
                    "user_id": self.user_id,
                    "knowledge_base_id": self.knowledge_base_id,
                }
            )

            prepared_documents.append(
                Document(
                    page_content=document.page_content.strip(),
                    metadata=self._sanitize_metadata(metadata),
                )
            )

            vector_id = self._create_vector_id(str(chunk_id))

            metadata["vector_id"] = vector_id
            document_ids.append(vector_id)

        logger.info(
            "chroma_documents_storage_started",
            organization_id=self.organization_id,
            user_id=self.user_id,
            knowledge_base_id=self.knowledge_base_id,
            document_count=len(prepared_documents),
        )

        try:
            stored_ids = self._store.add_documents(
                documents=prepared_documents,
                ids=document_ids,
            )
        except Exception as exc:
            raise VectorStoreError(
                message="Documents could not be stored in Chroma.",
                details={
                    "document_count": len(prepared_documents),
                    "error_type": type(exc).__name__,
                },
            ) from exc

        logger.info(
            "chroma_documents_storage_completed",
            organization_id=self.organization_id,
            user_id=self.user_id,
            knowledge_base_id=self.knowledge_base_id,
            document_count=len(stored_ids),
        )

        return stored_ids

    def similarity_search(
        self,
        query: str,
        *,
        k: int | None = None,
        document_id: str | None = None,
    ) -> list[Document]:
        """
        Search only inside the authenticated user's organization,
        user account and selected knowledge base.
        """

        cleaned_query = query.strip()

        if not cleaned_query:
            raise VectorStoreError(
                message="The similarity-search query cannot be empty."
            )

        result_limit = k or settings.retrieval_top_k

        filter_conditions: list[dict[str, Any]] = [
            {
                "organization_id": {
                    "$eq": self.organization_id
                }
            },
            {
                "user_id": {
                    "$eq": self.user_id
                }
            },
            {
                "knowledge_base_id": {
                    "$eq": self.knowledge_base_id
                }
            },
        ]

        if document_id is not None:
            filter_conditions.append(
                {
                    "document_id": {
                        "$eq": document_id
                    }
                }
            )

        metadata_filter: dict[str, Any] = {
            "$and": filter_conditions
        }

        try:
            results = self._store.similarity_search(
                query=cleaned_query,
                k=result_limit,
                filter=metadata_filter,
            )
        except Exception as exc:
            raise VectorStoreError(
                message="Chroma similarity search failed.",
                details={
                    "organization_id": self.organization_id,
                    "user_id": self.user_id,
                    "knowledge_base_id": self.knowledge_base_id,
                    "error_type": type(exc).__name__,
                },
            ) from exc

        logger.info(
            "chroma_similarity_search_completed",
            organization_id=self.organization_id,
            user_id=self.user_id,
            knowledge_base_id=self.knowledge_base_id,
            result_count=len(results),
            requested_results=result_limit,
        )

        return results

    def delete_chunks(
        self,
        chunk_ids: list[str],
    ) -> None:
        """
        Delete known chunk IDs.

        MySQL should later store each document's chunk IDs so they can
        be removed when a user deletes a PDF or their account.
        """

        cleaned_ids = [
            chunk_id.strip()
            for chunk_id in chunk_ids
            if chunk_id.strip()
        ]

        if not cleaned_ids:
            raise VectorStoreError(
                message="No chunk IDs were provided for deletion."
            )

        try:
            self._store.delete(ids=cleaned_ids)
        except Exception as exc:
            raise VectorStoreError(
                message="Chunks could not be deleted from Chroma.",
                details={
                    "chunk_count": len(cleaned_ids),
                    "error_type": type(exc).__name__,
                },
            ) from exc

        logger.info(
            "chroma_chunks_deleted",
            organization_id=self.organization_id,
            user_id=self.user_id,
            knowledge_base_id=self.knowledge_base_id,
            chunk_count=len(cleaned_ids),
        )

    def close(self) -> None:
        """Close the underlying Chroma client when supported."""

        close_method = getattr(self._client, "close", None)

        if callable(close_method):
            close_method()

    def _ensure_tenant_and_database(
        self,
        *,
        chroma_settings: ChromaSettings,
    ) -> None:
        """
        Create the organization tenant and its database if they
        do not already exist.
        """

        admin_client = chromadb.AdminClient(
            settings=chroma_settings
        )

        try:
            admin_client.get_tenant(
                name=self.tenant_name
            )
        except NotFoundError:
            try:
                admin_client.create_tenant(
                    name=self.tenant_name
                )
            except UniqueConstraintError:
                # Another request may have created it simultaneously.
                pass

        try:
            admin_client.get_database(
                name=self.database_name,
                tenant=self.tenant_name,
            )
        except NotFoundError:
            try:
                admin_client.create_database(
                    name=self.database_name,
                    tenant=self.tenant_name,
                )
            except UniqueConstraintError:
                # Another request may have created it simultaneously.
                pass

    def _validate_existing_ownership(
        self,
        *,
        metadata: dict[str, Any],
        position: int,
    ) -> None:
        expected_values = {
            "organization_id": self.organization_id,
            "user_id": self.user_id,
            "knowledge_base_id": self.knowledge_base_id,
        }

        for field_name, expected_value in expected_values.items():
            existing_value = metadata.get(field_name)

            if (
                existing_value is not None
                and str(existing_value) != expected_value
            ):
                raise VectorStoreError(
                    message=(
                        "Document ownership metadata does not match "
                        "the active vector-store namespace."
                    ),
                    details={
                        "position": position,
                        "field": field_name,
                    },
                )

    @staticmethod
    def _validate_identifier(
        value: str,
        *,
        field_name: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise VectorStoreError(
                message=f"{field_name} cannot be empty."
            )

        return cleaned_value

    @staticmethod
    def _create_namespace_name(
        *,
        prefix: str,
        value: str,
    ) -> str:
        """
        Produce a stable Chroma-safe name without exposing the
        original organization or knowledge-base identifier.
        """

        digest = sha256(
            value.encode("utf-8")
        ).hexdigest()[:24]

        return f"{prefix}_{digest}"

    @staticmethod
    def _sanitize_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, str | int | float | bool]:
        allowed_types = (
            str,
            int,
            float,
            bool,
        )

        return {
            str(key): value
            for key, value in metadata.items()
            if isinstance(value, allowed_types)
        }

    def _create_vector_id(self, chunk_id: str) -> str:
        value = (
            f"{self.organization_id}:"
            f"{self.user_id}:"
            f"{self.knowledge_base_id}:"
            f"{chunk_id}"
        )

        return sha256(value.encode("utf-8")).hexdigest()