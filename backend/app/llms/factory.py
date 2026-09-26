from backend.app.core.config import settings
from backend.app.core.exceptions import ConfigurationError
from backend.app.llms.base import BaseLLMProvider
from backend.app.llms.gemini_ai import GeminiLLMProvider
from backend.app.llms.openai_provider import OpenAILLMProvider


def get_llm_provider() -> BaseLLMProvider:
    """Return the provider selected through environment settings."""

    provider_name = settings.llm_provider.strip().lower()

    if provider_name == "gemini":
        return GeminiLLMProvider()

    if provider_name == "openai":
        return OpenAILLMProvider()

    raise ConfigurationError(
        message=(
            f"Unsupported LLM provider: "
            f"{settings.llm_provider}"
        ),
        details={
            "supported_providers": [
                "gemini",
                "openai",
            ],
        },
    )