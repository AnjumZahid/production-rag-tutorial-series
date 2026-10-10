from backend.app.auth.jwt import JWTService
from backend.app.core.exceptions import AuthenticationError


TEST_SECRET = "test-secret-key-for-jwt-auth-tests"


def build_jwt_service(
    *,
    issuer: str = "rag-app",
    audience: str = "rag-app-api",
) -> JWTService:
    return JWTService(
        secret_key=TEST_SECRET,
        algorithm="HS256",
        issuer=issuer,
        audience=audience,
        access_token_expire_minutes=60,
        refresh_token_expire_days=30,
        leeway_seconds=0,
    )


def expect_auth_error(
    callback,
    message: str,
) -> None:
    try:
        callback()
    except AuthenticationError:
        print(message)
        return

    raise AssertionError(
        "Expected AuthenticationError, but no error was raised."
    )


def main() -> None:
    print("=== JWT AUTHENTICATION TEST ===")

    service = build_jwt_service()

    access_token = service.create_access_token(
        user_id="test-user",
        organization_id="test-org",
    )

    access_claims = service.decode_access_token(access_token)

    assert access_claims.user_id == "test-user"
    assert access_claims.organization_id == "test-org"
    assert access_claims.token_type == "access"

    print("Valid access token confirmed.")
    print("User claim confirmed.")
    print("Organization claim confirmed.")

    refresh_token = service.create_refresh_token(
        user_id="test-user",
        organization_id="test-org",
    )

    refresh_claims = service.decode_refresh_token(refresh_token)

    assert refresh_claims.user_id == "test-user"
    assert refresh_claims.organization_id == "test-org"
    assert refresh_claims.token_type == "refresh"

    print("Valid refresh token confirmed.")

    expired_token = service.create_access_token(
        user_id="test-user",
        organization_id="test-org",
        expires_minutes=-1,
    )

    expect_auth_error(
        lambda: service.decode_access_token(expired_token),
        "Expired token rejected.",
    )

    wrong_audience_service = build_jwt_service(
        audience="wrong-audience"
    )

    wrong_audience_token = wrong_audience_service.create_access_token(
        user_id="test-user",
        organization_id="test-org",
    )

    expect_auth_error(
        lambda: service.decode_access_token(wrong_audience_token),
        "Wrong audience rejected.",
    )

    wrong_issuer_service = build_jwt_service(
        issuer="wrong-issuer"
    )

    wrong_issuer_token = wrong_issuer_service.create_access_token(
        user_id="test-user",
        organization_id="test-org",
    )

    expect_auth_error(
        lambda: service.decode_access_token(wrong_issuer_token),
        "Wrong issuer rejected.",
    )

    expect_auth_error(
        lambda: service.decode_access_token("invalid.token.value"),
        "Invalid signature/token rejected.",
    )

    expect_auth_error(
        lambda: service.decode_access_token(refresh_token),
        "Wrong token type rejected.",
    )

    print("JWT authentication test passed successfully.")


if __name__ == "__main__":
    main()

# uv run python -m tests.test_jwt_auth