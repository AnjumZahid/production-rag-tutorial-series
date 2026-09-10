from collections import Counter

from fastapi.routing import APIRoute

from backend.app.api.app import create_app


REQUIRED_OPERATIONS: dict[
    str,
    set[str],
] = {
    "/api/v1/health": {
        "get",
    },
    "/api/v1/health/live": {
        "get",
    },
    "/api/v1/health/ready": {
        "get",
    },
    "/api/v1/auth/register": {
        "post",
    },
    "/api/v1/auth/login": {
        "post",
    },
    "/api/v1/auth/refresh": {
        "post",
    },
    "/api/v1/auth/logout": {
        "post",
    },
    "/api/v1/auth/me": {
        "get",
    },
    "/api/v1/organizations/current": {
        "get",
    },
    "/api/v1/organizations/current/members": {
        "get",
        "post",
    },
    (
        "/api/v1/organizations/current/"
        "members/{membership_id}/role"
    ): {
        "patch",
    },
    (
        "/api/v1/organizations/current/"
        "members/{membership_id}"
    ): {
        "delete",
    },
    "/api/v1/documents": {
        "get",
        "post",
    },
    "/api/v1/documents/{document_id}": {
        "get",
        "delete",
    },
    "/api/v1/rag/query": {
        "post",
    },
}


HTTP_METHODS = {
    "get",
    "post",
    "put",
    "patch",
    "delete",
    "options",
    "head",
}


def verify_required_operations(
    schema: dict,
) -> None:
    """
    Confirm all frontend-required API operations exist.
    """

    paths = schema.get(
        "paths",
        {},
    )

    for (
        path,
        required_methods,
    ) in REQUIRED_OPERATIONS.items():

        assert path in paths, (
            f"Required API path is missing: {path}"
        )

        available_methods = {
            method.lower()
            for method in paths[path]
            if method.lower()
            in HTTP_METHODS
        }

        missing_methods = (
            required_methods
            - available_methods
        )

        assert not missing_methods, (
            f"Missing methods for {path}: "
            f"{sorted(missing_methods)}"
        )


def verify_unique_operation_ids(
    schema: dict,
) -> None:
    """
    Confirm every generated OpenAPI operation ID
    exists and is unique.
    """

    operation_ids: list[str] = []

    for path_item in schema.get(
        "paths",
        {},
    ).values():

        for (
            method,
            operation,
        ) in path_item.items():

            if (
                method.lower()
                not in HTTP_METHODS
                or not isinstance(
                    operation,
                    dict,
                )
            ):
                continue

            operation_id = (
                operation.get(
                    "operationId"
                )
            )

            assert operation_id, (
                "An OpenAPI operation "
                "is missing its operationId."
            )

            operation_ids.append(
                str(operation_id)
            )

    duplicates = [
        operation_id
        for (
            operation_id,
            count,
        ) in Counter(
            operation_ids
        ).items()
        if count > 1
    ]

    assert not duplicates, (
        "Duplicate OpenAPI operation IDs: "
        f"{duplicates}"
    )


def verify_bearer_security(
    schema: dict,
) -> None:
    """
    Confirm Swagger/OpenAPI exposes
    HTTP Bearer authentication.
    """

    security_schemes = (
        schema.get(
            "components",
            {},
        ).get(
            "securitySchemes",
            {},
        )
    )

    bearer_scheme_found = any(
        scheme.get(
            "type"
        ) == "http"
        and str(
            scheme.get(
                "scheme",
                "",
            )
        ).lower()
        == "bearer"
        for scheme
        in security_schemes.values()
    )

    assert bearer_scheme_found, (
        "OpenAPI does not contain "
        "an HTTP Bearer security scheme."
    )


def verify_no_duplicate_routes(
    app,
) -> None:
    """
    Detect duplicate FastAPI path +
    HTTP-method registrations.
    """

    route_pairs: list[
        tuple[str, str]
    ] = []

    for route in app.routes:

        if not isinstance(
            route,
            APIRoute,
        ):
            continue

        for method in route.methods:

            normalized_method = (
                method.upper()
            )

            if normalized_method in {
                "HEAD",
                "OPTIONS",
            }:
                continue

            route_pairs.append(
                (
                    route.path,
                    normalized_method,
                )
            )

    duplicates = [
        pair
        for (
            pair,
            count,
        ) in Counter(
            route_pairs
        ).items()
        if count > 1
    ]

    assert not duplicates, (
        "Duplicate FastAPI routes "
        f"detected: {duplicates}"
    )


def main() -> None:
    app = create_app()

    schema = app.openapi()

    verify_required_operations(
        schema
    )

    verify_unique_operation_ids(
        schema
    )

    verify_bearer_security(
        schema
    )

    verify_no_duplicate_routes(
        app
    )

    print(
        "\n=== BACKEND CONTRACT TEST ==="
    )

    print(
        "Required API paths confirmed."
    )

    print(
        "Required HTTP methods confirmed."
    )

    print(
        "Unique OpenAPI operation IDs "
        "confirmed."
    )

    print(
        "Bearer authentication scheme "
        "confirmed."
    )

    print(
        "No duplicate route "
        "registrations found."
    )

    print(
        "Backend contract test "
        "passed successfully."
    )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_backend_contract

# uv run python -m py_compile `
#     scripts/export_openapi.py `
#     tests/test_backend_contract.py