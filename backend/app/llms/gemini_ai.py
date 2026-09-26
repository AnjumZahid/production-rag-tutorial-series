# uv add google-genai

import time

from google import genai
from google.genai import errors, types

from backend.app.core.config import settings
from backend.app.core.exceptions import (
    ConfigurationError,
    LLMProviderError,
)
from backend.app.core.logging import get_logger
from backend.app.llms.base import BaseLLMProvider


logger = get_logger(__name__)


RETRYABLE_STATUS_CODES = {
    408,
    429,
    500,
    502,
    503,
    504,
}


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini implementation of the application's LLM interface.

    The provider uses the Google Gen AI SDK and generate_content().
    """

    def __init__(
        self,
        *,
        model_name: str | None = None,
    ) -> None:
        if settings.gemini_api_key is None:
            raise ConfigurationError(
                message=(
                    "GEMINI_API_KEY is missing from the environment."
                )
            )

        self.model_name = (
            model_name
            or settings.gemini_llm_model
        )

        self.max_retries = (
            settings.gemini_llm_max_retries
        )

        self.initial_retry_delay_seconds = (
            settings.gemini_llm_initial_retry_delay_seconds
        )

        self.max_retry_delay_seconds = (
            settings.gemini_llm_max_retry_delay_seconds
        )

        timeout_milliseconds = int(
            settings.gemini_llm_timeout_seconds * 1000
        )

        self.client = genai.Client(
            api_key=(
                settings.gemini_api_key.get_secret_value()
            ),
            http_options=types.HttpOptions(
                timeout=timeout_milliseconds,
            ),
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text response using Gemini."""

        normalized_system_prompt = system_prompt.strip()
        normalized_user_prompt = user_prompt.strip()

        if not normalized_system_prompt:
            raise LLMProviderError(
                message="The system prompt cannot be empty."
            )

        if not normalized_user_prompt:
            raise LLMProviderError(
                message="The user prompt cannot be empty."
            )

        logger.info(
            "gemini_generation_started",
            model=self.model_name,
            system_prompt_length=len(
                normalized_system_prompt
            ),
            user_prompt_length=len(
                normalized_user_prompt
            ),
        )

        response = self._generate_with_retries(
            system_prompt=normalized_system_prompt,
            user_prompt=normalized_user_prompt,
        )

        output_text = getattr(
            response,
            "text",
            None,
        )

        if not isinstance(output_text, str):
            raise LLMProviderError(
                message="Gemini returned a non-text response.",
                details={
                    "provider": "gemini",
                    "model": self.model_name,
                    "finish_reason": self._get_finish_reason(
                        response
                    ),
                },
            )

        normalized_output = output_text.strip()

        if not normalized_output:
            raise LLMProviderError(
                message="Gemini returned an empty response.",
                details={
                    "provider": "gemini",
                    "model": self.model_name,
                    "finish_reason": self._get_finish_reason(
                        response
                    ),
                },
            )

        logger.info(
            "gemini_generation_completed",
            model=self.model_name,
            output_length=len(normalized_output),
        )

        return normalized_output

    def _generate_with_retries(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):
        """Call Gemini and retry transient API errors."""

        for attempt in range(
            self.max_retries + 1
        ):
            try:
                return self.client.models.generate_content(
                    model=self.model_name,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        candidate_count=1,
                        max_output_tokens=(
                            settings.gemini_llm_max_output_tokens
                        ),
                        temperature=(
                            settings.gemini_llm_temperature
                        ),
                        thinking_config=types.ThinkingConfig(
                            thinking_budget=(
                                settings
                                .gemini_llm_thinking_budget
                            ),
                        ),
                    ),
                )

            except errors.APIError as exc:
                status_code = self._safe_status_code(
                    getattr(exc, "code", None)
                )

                should_retry = (
                    status_code in RETRYABLE_STATUS_CODES
                    and attempt < self.max_retries
                )

                if not should_retry:
                    logger.exception(
                        "gemini_generation_failed",
                        model=self.model_name,
                        status_code=status_code,
                        error_type=type(exc).__name__,
                    )

                    raise LLMProviderError(
                        details={
                            "provider": "gemini",
                            "model": self.model_name,
                            "status_code": status_code,
                            "error_type": (
                                type(exc).__name__
                            ),
                            "error_message": str(exc),
                        }
                    ) from exc

                delay = min(
                    (
                        self.initial_retry_delay_seconds
                        * (2**attempt)
                    ),
                    self.max_retry_delay_seconds,
                )

                logger.warning(
                    "gemini_generation_retrying",
                    model=self.model_name,
                    attempt=attempt + 1,
                    maximum_attempts=(
                        self.max_retries + 1
                    ),
                    status_code=status_code,
                    retry_delay_seconds=delay,
                )

                time.sleep(delay)

            except Exception as exc:
                logger.exception(
                    "gemini_generation_failed",
                    model=self.model_name,
                    error_type=type(exc).__name__,
                )

                raise LLMProviderError(
                    details={
                        "provider": "gemini",
                        "model": self.model_name,
                        "error_type": type(exc).__name__,
                        "error_message": str(exc),
                    }
                ) from exc

        raise LLMProviderError(
            message=(
                "Gemini generation failed after all "
                "retry attempts."
            ),
            details={
                "provider": "gemini",
                "model": self.model_name,
            },
        )

    @staticmethod
    def _safe_status_code(
        value: object,
    ) -> int | None:
        """Convert an API status code to an integer."""

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _get_finish_reason(
        response: object,
    ) -> str | None:
        """Extract the first candidate finish reason safely."""

        candidates = getattr(
            response,
            "candidates",
            None,
        )

        if not candidates:
            return None

        finish_reason = getattr(
            candidates[0],
            "finish_reason",
            None,
        )

        if finish_reason is None:
            return None

        return str(finish_reason)

    def close(self) -> None:
        """Close the underlying Google client."""

        self.client.close()