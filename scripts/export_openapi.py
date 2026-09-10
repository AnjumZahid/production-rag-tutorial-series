import json
from pathlib import Path

from backend.app.api.app import (
    create_app,
)


PROJECT_ROOT = (
    Path(__file__)
    .resolve()
    .parents[1]
)


OUTPUT_DIRECTORY = (
    PROJECT_ROOT
    / "frontend_contract"
)


OUTPUT_FILE = (
    OUTPUT_DIRECTORY
    / "openapi.json"
)


def main() -> None:
    """
    Export the frontend-facing
    machine-readable OpenAPI contract.
    """

    app = create_app()

    schema = app.openapi()

    OUTPUT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            schema,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        "OpenAPI contract exported:"
    )

    print(
        OUTPUT_FILE
    )


if __name__ == "__main__":
    main()


# uv run python -m scripts.export_openapi