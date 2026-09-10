from typing import Literal

from pydantic import BaseModel


class LivenessResponse(
    BaseModel
):
    status: Literal[
        "alive"
    ]

    application: str

    environment: str


class DependencyHealthResponse(
    BaseModel
):
    status: Literal[
        "ok",
        "unavailable",
        "disabled",
    ]


class ReadinessChecksResponse(
    BaseModel
):
    database: (
        DependencyHealthResponse
    )

    redis: (
        DependencyHealthResponse
    )


class ReadinessResponse(
    BaseModel
):
    status: Literal[
        "ready",
        "not_ready",
    ]

    checks: (
        ReadinessChecksResponse
    )