from collections.abc import (
    Awaitable,
    Callable,
)

from fastapi import (
    Depends,
    Request,
    Response,
)

from backend.app.api.dependencies import (
    OrganizationAccess,
    get_organization_access,
)
from backend.app.rate_limiting.exceptions import (
    RateLimitExceededError,
)
from backend.app.rate_limiting.service import (
    RateLimitDecision,
    get_rate_limiter,
)


RateLimitDependency = Callable[
    ...,
    Awaitable[None],
]


# =============================================================
# Client identifier
# =============================================================


def _client_identifier(
    request: Request,
) -> str:
    """
    Return direct request client IP.

    When deploying behind a reverse proxy later,
    proxy-header trust must be configured correctly
    before trusting forwarded addresses.
    """

    client = request.client

    if client is None:
        return "unknown-client"

    return str(
        client.host
    )


# =============================================================
# Response headers
# =============================================================


def _apply_headers(
    response: Response,
    decision: RateLimitDecision,
) -> None:
    """
    Attach endpoint-specific rate-limit headers.
    """

    response.headers[
        "X-RateLimit-Limit"
    ] = str(
        decision.limit
    )

    response.headers[
        "X-RateLimit-Remaining"
    ] = str(
        decision.remaining
    )

    response.headers[
        "X-RateLimit-Reset"
    ] = str(
        decision.reset_after
    )


# =============================================================
# Blocked decision
# =============================================================


def _raise_if_blocked(
    *,
    scope: str,
    decision: RateLimitDecision,
) -> None:
    """
    Raise structured HTTP 429 when the
    limit has been exceeded.
    """

    if decision.allowed:
        return

    raise RateLimitExceededError(
        scope=scope,
        limit=decision.limit,
        remaining=(
            decision.remaining
        ),
        retry_after=(
            decision.retry_after
        ),
        reset_after=(
            decision.reset_after
        ),
    )


# =============================================================
# IP-based dependency factory
# =============================================================


def require_ip_rate_limit(
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> RateLimitDependency:
    """
    Create an IP-based rate-limit dependency.

    Used for:

        registration
        login
        refresh
    """

    async def dependency(
        request: Request,
        response: Response,
    ) -> None:
        decision = (
            await get_rate_limiter().check(
                scope=scope,
                identifier=(
                    _client_identifier(
                        request
                    )
                ),
                limit=limit,
                window_seconds=(
                    window_seconds
                ),
            )
        )

        _apply_headers(
            response,
            decision,
        )

        _raise_if_blocked(
            scope=scope,
            decision=decision,
        )

    return dependency


# =============================================================
# Authenticated-user dependency factory
# =============================================================


def require_user_rate_limit(
    *,
    scope: str,
    limit: int,
    window_seconds: int,
) -> RateLimitDependency:
    """
    Create an authenticated organization+user
    rate-limit dependency.

    Identity comes from verified JWT and active
    organization membership, not client input.
    """

    async def dependency(
        response: Response,
        access: OrganizationAccess = Depends(
            get_organization_access
        ),
    ) -> None:
        identifier = (
            f"{access.organization_id}:"
            f"{access.user_id}"
        )

        decision = (
            await get_rate_limiter().check(
                scope=scope,
                identifier=identifier,
                limit=limit,
                window_seconds=(
                    window_seconds
                ),
            )
        )

        _apply_headers(
            response,
            decision,
        )

        _raise_if_blocked(
            scope=scope,
            decision=decision,
        )

    return dependency