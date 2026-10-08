from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AuthenticationError
from backend.app.database.session import get_session_factory
from backend.app.embeddings.factory import get_embedding_provider
from backend.app.llms import get_llm_provider


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    organization_id: str
    user_id: str


_embedding_provider = None
_llm_provider = None


async def get_database_session_dependency() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session


def get_request_identity(
    x_organization_id: Annotated[
        str | None,
        Header(alias="X-Organization-ID"),
    ] = None,
    x_user_id: Annotated[
        str | None,
        Header(alias="X-User-ID"),
    ] = None,
) -> RequestIdentity:
    if not x_organization_id:
        raise AuthenticationError(
            message="X-Organization-ID header is required."
        )

    if not x_user_id:
        raise AuthenticationError(
            message="X-User-ID header is required."
        )

    return RequestIdentity(
        organization_id=x_organization_id.strip(),
        user_id=x_user_id.strip(),
    )


def get_embedding_provider_dependency():
    global _embedding_provider

    if _embedding_provider is None:
        _embedding_provider = get_embedding_provider()

    return _embedding_provider


def get_llm_provider_dependency():
    global _llm_provider

    if _llm_provider is None:
        _llm_provider = get_llm_provider()

    return _llm_provider


async def close_shared_resources() -> None:
    global _embedding_provider
    global _llm_provider

    for resource in (
        _embedding_provider,
        _llm_provider,
    ):
        if resource is None:
            continue

        close_method = getattr(
            resource,
            "close",
            None,
        )

        if callable(close_method):
            close_method()

    _embedding_provider = None
    _llm_provider = None