import re
from time import perf_counter
from uuid import uuid4

from starlette.datastructures import (
    Headers,
    MutableHeaders,
)
from starlette.types import (
    ASGIApp,
    Message,
    Receive,
    Scope,
    Send,
)

from backend.app.core.logging import (
    get_logger,
)


logger = get_logger(__name__)


_REQUEST_ID_PATTERN = re.compile(
    r"^[A-Za-z0-9._-]{8,128}$"
)


class RequestSecurityMiddleware:
    """
    Central security middleware.

    Responsibilities:

    - Validate or generate request IDs.
    - Store request ID in request state.
    - Measure request duration.
    - Add security response headers.
    - Add trace headers.
    - Prevent authentication-response caching.
    - Optionally add HSTS.
    - Write structured request logs.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        enable_hsts: bool = False,
        hsts_max_age_seconds: int = 31_536_000,
    ) -> None:
        self.app = app

        self.enable_hsts = (
            enable_hsts
        )

        self.hsts_max_age_seconds = (
            hsts_max_age_seconds
        )

    # ---------------------------------------------------------
    # Request ID
    # ---------------------------------------------------------

    @staticmethod
    def _get_request_id(
        scope: Scope,
    ) -> str:
        """
        Keep a caller-provided request ID only when
        it matches the safe request-ID format.

        Otherwise generate a new random request ID.
        """

        headers = Headers(
            scope=scope
        )

        supplied_request_id = (
            headers.get(
                "x-request-id"
            )
        )

        if (
            supplied_request_id
            and _REQUEST_ID_PATTERN.fullmatch(
                supplied_request_id
            )
        ):
            return supplied_request_id

        return uuid4().hex

    # ---------------------------------------------------------
    # Client IP
    # ---------------------------------------------------------

    @staticmethod
    def _get_client_ip(
        scope: Scope,
    ) -> str | None:
        client = scope.get(
            "client"
        )

        if not client:
            return None

        return str(
            client[0]
        )

    # ---------------------------------------------------------
    # ASGI middleware execution
    # ---------------------------------------------------------

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        # Ignore websocket and other non-HTTP traffic.
        if scope["type"] != "http":
            await self.app(
                scope,
                receive,
                send,
            )

            return

        # -----------------------------------------------------
        # Request identity / tracing
        # -----------------------------------------------------

        request_id = (
            self._get_request_id(
                scope
            )
        )

        state = scope.get(
            "state"
        )

        if not isinstance(
            state,
            dict,
        ):
            state = {}

            scope["state"] = state

        state[
            "request_id"
        ] = request_id

        # -----------------------------------------------------
        # Safe request information
        #
        # Deliberately do NOT log:
        #
        # Authorization header
        # request body
        # query string
        # passwords
        # uploaded file contents
        # -----------------------------------------------------

        method = str(
            scope.get(
                "method",
                "",
            )
        )

        path = str(
            scope.get(
                "path",
                "",
            )
        )

        scheme = str(
            scope.get(
                "scheme",
                "http",
            )
        )

        client_ip = (
            self._get_client_ip(
                scope
            )
        )

        started_at = (
            perf_counter()
        )

        # Default used only if a response is not
        # successfully started.
        response_status = 500

        # -----------------------------------------------------
        # Response wrapper
        # -----------------------------------------------------

        async def send_wrapper(
            message: Message,
        ) -> None:
            nonlocal response_status

            if (
                message["type"]
                == "http.response.start"
            ):
                response_status = int(
                    message[
                        "status"
                    ]
                )

                duration_ms = (
                    perf_counter()
                    - started_at
                ) * 1000

                response_headers = (
                    MutableHeaders(
                        scope=message
                    )
                )

                # ---------------------------------------------
                # Request tracing
                # ---------------------------------------------

                response_headers[
                    "X-Request-ID"
                ] = request_id

                response_headers[
                    "X-Process-Time-Ms"
                ] = (
                    f"{duration_ms:.2f}"
                )

                # ---------------------------------------------
                # Browser security headers
                # ---------------------------------------------

                response_headers[
                    "X-Content-Type-Options"
                ] = "nosniff"

                response_headers[
                    "X-Frame-Options"
                ] = "DENY"

                response_headers[
                    "Referrer-Policy"
                ] = "no-referrer"

                response_headers[
                    "Permissions-Policy"
                ] = (
                    "camera=(), "
                    "microphone=(), "
                    "geolocation=()"
                )

                # ---------------------------------------------
                # Do not cache authentication responses
                # ---------------------------------------------

                if path.startswith(
                    "/api/v1/auth"
                ):
                    response_headers[
                        "Cache-Control"
                    ] = "no-store"

                # ---------------------------------------------
                # HSTS
                #
                # Only emit HSTS over HTTPS.
                # Never use HSTS for local HTTP development.
                # ---------------------------------------------

                if (
                    self.enable_hsts
                    and scheme == "https"
                ):
                    response_headers[
                        "Strict-Transport-Security"
                    ] = (
                        "max-age="
                        f"{self.hsts_max_age_seconds}; "
                        "includeSubDomains"
                    )

            await send(
                message
            )

        # -----------------------------------------------------
        # Execute application
        # -----------------------------------------------------

        try:
            await self.app(
                scope,
                receive,
                send_wrapper,
            )

        # -----------------------------------------------------
        # Structured failure logging
        # -----------------------------------------------------

        except Exception as exc:
            duration_ms = (
                perf_counter()
                - started_at
            ) * 1000

            logger.error(
                "http_request_failed",
                request_id=(
                    request_id
                ),
                method=method,
                path=path,
                client_ip=(
                    client_ip
                ),
                duration_ms=round(
                    duration_ms,
                    2,
                ),
                error_type=(
                    type(exc).__name__
                ),
            )

            # Preserve existing FastAPI / Starlette
            # exception handling.
            raise

        # -----------------------------------------------------
        # Structured completion logging
        # -----------------------------------------------------

        else:
            duration_ms = (
                perf_counter()
                - started_at
            ) * 1000

            logger.info(
                "http_request_completed",
                request_id=(
                    request_id
                ),
                method=method,
                path=path,
                status_code=(
                    response_status
                ),
                client_ip=(
                    client_ip
                ),
                duration_ms=round(
                    duration_ms,
                    2,
                ),
            )