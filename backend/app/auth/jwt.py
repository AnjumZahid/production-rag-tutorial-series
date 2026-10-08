# uv add PyJWT

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from backend.app.core.config import settings
from backend.app.core.exceptions import AuthenticationError


@dataclass(frozen=True, slots=True)
class AccessTokenClaims:
    """Verified access-token claims used by the API."""

    user_id: str
    organization_id: str
    token_id: str
    expires_at: datetime


def create_access_token(
    *,
    user_id: str,
    organization_id: str,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT access token."""

    normalized_user_id = user_id.strip()
    normalized_organization_id = organization_id.strip()

    if not normalized_user_id:
        raise ValueError("user_id cannot be empty.")

    if not normalized_organization_id:
        raise ValueError("organization_id cannot be empty.")

    now = datetime.now(timezone.utc)

    expiry_minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.auth_access_token_expire_minutes
    )

    expires_at = now + timedelta(
        minutes=expiry_minutes
    )

    payload = {
        "sub": normalized_user_id,
        "organization_id": normalized_organization_id,
        "type": "access",
        "jti": uuid4().hex,
        "iat": now,
        "exp": expires_at,
        "iss": settings.auth_jwt_issuer,
        "aud": settings.auth_jwt_audience,
    }

    return jwt.encode(
        payload,
        settings.auth_jwt_secret_key.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
    )


def decode_access_token(token: str) -> AccessTokenClaims:
    """Validate and decode a JWT access token."""

    if not token or not token.strip():
        raise AuthenticationError(
            message="Bearer token is required."
        )

    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret_key.get_secret_value(),
            algorithms=[settings.auth_jwt_algorithm],
            issuer=settings.auth_jwt_issuer,
            audience=settings.auth_jwt_audience,
            leeway=settings.auth_jwt_leeway_seconds,
            options={
                "require": [
                    "sub",
                    "organization_id",
                    "type",
                    "jti",
                    "iat",
                    "exp",
                    "iss",
                    "aud",
                ]
            },
        )

    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError(
            message="The access token has expired."
        ) from None

    except jwt.InvalidTokenError as exc:
        raise AuthenticationError(
            message="The access token is invalid."
        ) from None

    token_type = payload.get("type")
    if token_type != "access":
        raise AuthenticationError(
            message="Only access tokens are accepted."
        )

    user_id = str(payload.get("sub") or "").strip()
    organization_id = str(
        payload.get("organization_id") or ""
    ).strip()
    token_id = str(payload.get("jti") or "").strip()

    if not user_id:
        raise AuthenticationError(
            message="The access token is missing a user ID."
        )

    if not organization_id:
        raise AuthenticationError(
            message=(
                "The access token is missing an organization ID."
            )
        )

    if not token_id:
        raise AuthenticationError(
            message="The access token is missing a token ID."
        )

    expires_at_timestamp = payload.get("exp")
    expires_at = datetime.fromtimestamp(
        float(expires_at_timestamp),
        tz=timezone.utc,
    )

    return AccessTokenClaims(
        user_id=user_id,
        organization_id=organization_id,
        token_id=token_id,
        expires_at=expires_at,
    )