from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt

from backend.app.auth import (
    create_access_token,
    decode_access_token,
)
from backend.app.core.config import settings
from backend.app.core.exceptions import AuthenticationError


def make_raw_token(
    *,
    user_id: str = "test-user",
    organization_id: str = "test-org",
    token_type: str = "access",
    issuer: str | None = None,
    audience: str | None = None,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)

    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=60)
    )

    payload = {
        "sub": user_id,
        "organization_id": organization_id,
        "type": token_type,
        "jti": uuid4().hex,
        "iat": now,
        "exp": expires_at,
        "iss": issuer or settings.auth_jwt_issuer,
        "aud": audience or settings.auth_jwt_audience,
    }

    return jwt.encode(
        payload,
        secret_key
        or settings.auth_jwt_secret_key.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
    )


def assert_authentication_error(token: str) -> None:
    failed = False

    try:
        decode_access_token(token)

    except AuthenticationError:
        failed = True

    assert failed is True


def main() -> None:
    valid_token = create_access_token(
        user_id="test-user",
        organization_id="test-org",
        expires_minutes=60,
    )

    claims = decode_access_token(valid_token)

    assert claims.user_id == "test-user"
    assert claims.organization_id == "test-org"
    assert claims.token_id
    assert claims.expires_at > datetime.now(timezone.utc)

    expired_token = make_raw_token(
        expires_delta=timedelta(minutes=-10)
    )
    assert_authentication_error(expired_token)

    wrong_audience_token = make_raw_token(
        audience="wrong-audience"
    )
    assert_authentication_error(wrong_audience_token)

    wrong_issuer_token = make_raw_token(
        issuer="wrong-issuer"
    )
    assert_authentication_error(wrong_issuer_token)

    invalid_signature_token = make_raw_token(
        secret_key="wrong-secret"
    )
    assert_authentication_error(invalid_signature_token)

    wrong_type_token = make_raw_token(
        token_type="refresh"
    )
    assert_authentication_error(wrong_type_token)

    print("\n=== JWT AUTHENTICATION TEST ===")
    print("Valid token confirmed.")
    print("User claim confirmed.")
    print("Organization claim confirmed.")
    print("Expired token rejected.")
    print("Wrong audience rejected.")
    print("Wrong issuer rejected.")
    print("Invalid signature/token rejected.")
    print("JWT authentication test passed successfully.")


if __name__ == "__main__":
    main()

# uv run python -m tests.test_jwt_auth