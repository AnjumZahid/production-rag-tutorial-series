from collections.abc import (
    AsyncGenerator,
    Callable,
)
from dataclasses import dataclass

from fastapi import Depends
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth import decode_access_token
from backend.app.auth.roles import (
    OrganizationRole,
)
from backend.app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
)
from backend.app.database.repositories.membership_repository import (
    MembershipRepository,
)
from backend.app.database.session import (
    get_session_factory,
)
from backend.app.embeddings.base import (
    BaseEmbeddingProvider,
)
from backend.app.embeddings.factory import (
    get_embedding_provider,
)
from backend.app.llms import (
    BaseLLMProvider,
    get_llm_provider,
)


@dataclass(frozen=True, slots=True)
class RequestIdentity:
    organization_id: str
    user_id: str
    token_id: str


@dataclass(frozen=True, slots=True)
class OrganizationAccess:
    organization_id: str
    user_id: str
    membership_id: str
    role: str


bearer_scheme = HTTPBearer(
    scheme_name="BearerAuth",
    auto_error=False,
)

_embedding_provider: BaseEmbeddingProvider | None = None
_llm_provider: BaseLLMProvider | None = None


async def get_database_session_dependency() -> AsyncGenerator[
    AsyncSession,
    None,
]:
    session_factory = get_session_factory()

    async with session_factory() as session:
        yield session


def get_request_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> RequestIdentity:
    if credentials is None:
        raise AuthenticationError(
            message=(
                "Bearer access token is required."
            )
        )

    if credentials.scheme.lower() != "bearer":
        raise AuthenticationError(
            message=(
                "Bearer authentication is required."
            )
        )

    claims = decode_access_token(
        credentials.credentials
    )

    return RequestIdentity(
        organization_id=claims.organization_id,
        user_id=claims.user_id,
        token_id=claims.token_id,
    )


async def get_organization_access(
    identity: RequestIdentity = Depends(
        get_request_identity
    ),
    session: AsyncSession = Depends(
        get_database_session_dependency
    ),
) -> OrganizationAccess:
    """
    Validate JWT identity against an active
    organization membership.
    """

    repository = MembershipRepository(
        session
    )

    membership = (
        await repository.get_active_membership(
            organization_id=identity.organization_id,
            user_id=identity.user_id,
        )
    )

    if membership is None:
        raise AuthorizationError(
            message=(
                "You do not have an active membership "
                "in this organization."
            )
        )

    try:
        normalized_role = OrganizationRole(
            membership.role
        )
    except ValueError as exc:
        raise AuthorizationError(
            message=(
                "Your organization membership "
                "has an invalid role."
            )
        ) from exc

    return OrganizationAccess(
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        membership_id=membership.id,
        role=normalized_role.value,
    )


def require_organization_roles(
    *roles: OrganizationRole,
) -> Callable:
    """
    Build a reusable role dependency.

    Example:

        Depends(
            require_organization_roles(
                OrganizationRole.OWNER,
                OrganizationRole.ADMIN,
            )
        )
    """

    allowed_roles = frozenset(
        role.value
        for role in roles
    )

    async def dependency(
        access: OrganizationAccess = Depends(
            get_organization_access
        ),
    ) -> OrganizationAccess:
        if access.role not in allowed_roles:
            raise AuthorizationError(
                message=(
                    "Your organization role does not "
                    "permit this action."
                ),
                details={
                    "required_roles": sorted(
                        allowed_roles
                    ),
                    "current_role": access.role,
                },
            )

        return access

    return dependency


require_document_read_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
        OrganizationRole.VIEWER,
    )
)


require_document_write_access = (
    require_organization_roles(
        OrganizationRole.OWNER,
        OrganizationRole.ADMIN,
        OrganizationRole.MEMBER,
    )
)


def get_embedding_provider_dependency():
    global _embedding_provider

    if _embedding_provider is None:
        _embedding_provider = (
            get_embedding_provider()
        )

    return _embedding_provider


def get_llm_provider_dependency():
    global _llm_provider

    if _llm_provider is None:
        _llm_provider = (
            get_llm_provider()
        )

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