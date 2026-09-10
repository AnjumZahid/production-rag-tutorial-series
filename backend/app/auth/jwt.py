from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from backend.app.core.config import settings
from backend.app.core.exceptions import AuthenticationError


@dataclass(frozen=True, slots=True)
class TokenClaims:
    user_id: str
    organization_id: str
    token_id: str
    token_type: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class JWTService:
    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        issuer: str,
        audience: str,
        access_token_expire_minutes: int,
        refresh_token_expire_days: int,
        leeway_seconds: int,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.issuer = issuer
        self.audience = audience
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days
        self.leeway_seconds = leeway_seconds

    def create_access_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        expires_minutes: int | None = None,
    ) -> str:
        expiry_minutes = (
            expires_minutes
            if expires_minutes is not None
            else self.access_token_expire_minutes
        )

        return self._create_token(
            user_id=user_id,
            organization_id=organization_id,
            token_type="access",
            expires_delta=timedelta(minutes=expiry_minutes),
        )

    def create_refresh_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        expires_days: int | None = None,
    ) -> str:
        expiry_days = (
            expires_days
            if expires_days is not None
            else self.refresh_token_expire_days
        )

        return self._create_token(
            user_id=user_id,
            organization_id=organization_id,
            token_type="refresh",
            expires_delta=timedelta(days=expiry_days),
        )

    def create_token_pair(
        self,
        *,
        user_id: str,
        organization_id: str,
    ) -> TokenPair:
        access_token = self.create_access_token(
            user_id=user_id,
            organization_id=organization_id,
        )

        refresh_token = self.create_refresh_token(
            user_id=user_id,
            organization_id=organization_id,
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self.access_token_expire_minutes * 60,
        )

    def decode_access_token(
        self,
        token: str,
    ) -> TokenClaims:
        return self._decode_token(
            token=token,
            expected_token_type="access",
        )

    def decode_refresh_token(
        self,
        token: str,
    ) -> TokenClaims:
        return self._decode_token(
            token=token,
            expected_token_type="refresh",
        )

    def _create_token(
        self,
        *,
        user_id: str,
        organization_id: str,
        token_type: str,
        expires_delta: timedelta,
    ) -> str:
        normalized_user_id = user_id.strip()
        normalized_organization_id = organization_id.strip()

        if not normalized_user_id:
            raise ValueError("user_id cannot be empty.")

        if not normalized_organization_id:
            raise ValueError("organization_id cannot be empty.")

        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        payload = {
            "sub": normalized_user_id,
            "organization_id": normalized_organization_id,
            "type": token_type,
            "jti": uuid4().hex,
            "iat": now,
            "exp": expires_at,
            "iss": self.issuer,
            "aud": self.audience,
        }

        return jwt.encode(
            payload,
            self.secret_key,
            algorithm=self.algorithm,
        )

    def _decode_token(
        self,
        *,
        token: str,
        expected_token_type: str,
    ) -> TokenClaims:
        if not token or not token.strip():
            raise AuthenticationError(
                message="Bearer token is required."
            )

        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                issuer=self.issuer,
                audience=self.audience,
                leeway=self.leeway_seconds,
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
                    ],
                },
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationError(
                message="The token has expired."
            ) from None

        except jwt.InvalidTokenError:
            raise AuthenticationError(
                message="The token is invalid."
            ) from None

        token_type = str(payload.get("type") or "").strip()

        if token_type != expected_token_type:
            raise AuthenticationError(
                message=(
                    f"Expected {expected_token_type} token, "
                    f"but received {token_type or 'unknown'} token."
                )
            )

        user_id = str(payload.get("sub") or "").strip()
        organization_id = str(
            payload.get("organization_id") or ""
        ).strip()
        token_id = str(payload.get("jti") or "").strip()

        if not user_id:
            raise AuthenticationError(
                message="The token is missing a user ID."
            )

        if not organization_id:
            raise AuthenticationError(
                message="The token is missing an organization ID."
            )

        if not token_id:
            raise AuthenticationError(
                message="The token is missing a token ID."
            )

        expires_at = datetime.fromtimestamp(
            float(payload["exp"]),
            tz=timezone.utc,
        )

        return TokenClaims(
            user_id=user_id,
            organization_id=organization_id,
            token_id=token_id,
            token_type=token_type,
            expires_at=expires_at,
        )


jwt_service = JWTService(
    secret_key=settings.auth_jwt_secret_key.get_secret_value(),
    algorithm=settings.auth_jwt_algorithm,
    issuer=settings.auth_jwt_issuer,
    audience=settings.auth_jwt_audience,
    access_token_expire_minutes=(
        settings.auth_access_token_expire_minutes
    ),
    refresh_token_expire_days=(
        settings.auth_refresh_token_expire_days
    ),
    leeway_seconds=settings.auth_jwt_leeway_seconds,
)


def create_access_token(
    *,
    user_id: str,
    organization_id: str,
    expires_minutes: int | None = None,
) -> str:
    return jwt_service.create_access_token(
        user_id=user_id,
        organization_id=organization_id,
        expires_minutes=expires_minutes,
    )


def create_refresh_token(
    *,
    user_id: str,
    organization_id: str,
    expires_days: int | None = None,
) -> str:
    return jwt_service.create_refresh_token(
        user_id=user_id,
        organization_id=organization_id,
        expires_days=expires_days,
    )


def create_token_pair(
    *,
    user_id: str,
    organization_id: str,
) -> TokenPair:
    return jwt_service.create_token_pair(
        user_id=user_id,
        organization_id=organization_id,
    )


def decode_access_token(
    token: str,
) -> TokenClaims:
    return jwt_service.decode_access_token(token)


def decode_refresh_token(
    token: str,
) -> TokenClaims:
    return jwt_service.decode_refresh_token(token)