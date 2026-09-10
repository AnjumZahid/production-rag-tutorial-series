from backend.app.core.exceptions import (
    AppError,
)


class RateLimitExceededError(AppError):
    """
    Raised when one endpoint-specific
    rate limit has been exceeded.
    """

    code = "RATE_LIMIT_EXCEEDED"

    default_message = (
        "Too many requests. "
        "Please try again later."
    )

    status_code = 429

    def __init__(
        self,
        *,
        scope: str,
        limit: int,
        remaining: int,
        retry_after: int,
        reset_after: int,
    ) -> None:
        super().__init__(
            details={
                "scope": scope,
                "limit": limit,
                "remaining": remaining,
                "retry_after": retry_after,
                "reset_after": reset_after,
            }
        )

        self.headers = {
            "Retry-After": str(
                retry_after
            ),
            "X-RateLimit-Limit": str(
                limit
            ),
            "X-RateLimit-Remaining": str(
                remaining
            ),
            "X-RateLimit-Reset": str(
                reset_after
            ),
        }


class RateLimitBackendError(AppError):
    """
    Raised when Redis is required for
    rate limiting but is unavailable.
    """

    code = "RATE_LIMIT_BACKEND_ERROR"

    default_message = (
        "The request-limiting service "
        "is unavailable."
    )

    status_code = 503