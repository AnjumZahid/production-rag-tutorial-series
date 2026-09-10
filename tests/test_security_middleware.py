from fastapi.testclient import (
    TestClient,
)

from backend.app.api.app import (
    create_app,
)


def main() -> None:
    app = create_app()

    valid_request_id = (
        "security-test-request-123"
    )

    with TestClient(
        app
    ) as client:

        # =====================================================
        # 1. Valid request ID must be preserved
        # =====================================================

        response = client.get(
            "/api/v1/health",
            headers={
                "Origin": (
                    "http://localhost:3000"
                ),
                "X-Request-ID": (
                    valid_request_id
                ),
            },
        )

        assert (
            response.status_code
            == 200
        )

        assert (
            response.headers[
                "x-request-id"
            ]
            == valid_request_id
        )

        # =====================================================
        # 2. Security headers
        # =====================================================

        assert (
            response.headers[
                "x-content-type-options"
            ]
            == "nosniff"
        )

        assert (
            response.headers[
                "x-frame-options"
            ]
            == "DENY"
        )

        assert (
            response.headers[
                "referrer-policy"
            ]
            == "no-referrer"
        )

        assert (
            response.headers[
                "permissions-policy"
            ]
            == (
                "camera=(), "
                "microphone=(), "
                "geolocation=()"
            )
        )

        # =====================================================
        # 3. Process timing
        # =====================================================

        assert (
            "x-process-time-ms"
            in response.headers
        )

        process_time = float(
            response.headers[
                "x-process-time-ms"
            ]
        )

        assert process_time >= 0

        # =====================================================
        # 4. Allowed CORS origin
        # =====================================================

        assert (
            response.headers[
                "access-control-allow-origin"
            ]
            == "http://localhost:3000"
        )

        print(
            "\n=== SECURITY MIDDLEWARE TEST ==="
        )

        print(
            "Trusted request ID confirmed."
        )

        print(
            "Security headers confirmed."
        )

        print(
            "Process-time header confirmed."
        )

        print(
            "CORS origin confirmed."
        )

        # =====================================================
        # 5. Invalid request ID must be replaced
        # =====================================================

        invalid_id_response = (
            client.get(
                "/api/v1/health",
                headers={
                    "X-Request-ID": (
                        "bad request id!"
                    ),
                },
            )
        )

        assert (
            invalid_id_response.status_code
            == 200
        )

        generated_request_id = (
            invalid_id_response.headers[
                "x-request-id"
            ]
        )

        assert generated_request_id

        assert (
            generated_request_id
            != "bad request id!"
        )

        assert (
            len(
                generated_request_id
            )
            >= 8
        )

        print(
            "Invalid request ID "
            "replacement confirmed."
        )

        # =====================================================
        # 6. Auth response must not be cached
        #
        # This deliberately calls a nonexistent auth path.
        # The status can be 404; we only need to confirm that
        # anything under /api/v1/auth gets no-store.
        # =====================================================

        auth_cache_response = (
            client.get(
                "/api/v1/auth/"
                "security-cache-test"
            )
        )

        assert (
            auth_cache_response.headers[
                "cache-control"
            ]
            == "no-store"
        )

        print(
            "Authentication no-store "
            "policy confirmed."
        )

        # =====================================================
        # 7. Unexpected Host header must be rejected
        # =====================================================

        untrusted_host_response = (
            client.get(
                "/api/v1/health",
                headers={
                    "Host": (
                        "malicious.example"
                    ),
                },
            )
        )

        assert (
            untrusted_host_response.status_code
            == 400
        )

        print(
            "Untrusted host rejection "
            "confirmed."
        )

        # =====================================================
        # Final result
        # =====================================================

        print(
            "Security middleware test "
            "passed successfully."
        )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_security_middleware