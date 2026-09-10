from backend.app.api.app import (
    create_app,
)


app = create_app()


# uv run uvicorn backend.app.main:app --reload