from backend.app.core.exceptions import ConfigurationError
from backend.app.llms.base import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """
    Placeholder OpenAI provider.

    Gemini is the active provider in this step. A real OpenAI
    implementation can be added later without changing the RAG flow.
    """

    def __init__(self) -> None:
        raise ConfigurationError(
            message=(
                "OpenAI LLM provider is not implemented in this step. "
                "Set LLM_PROVIDER=gemini."
            )
        )

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text response."""

        raise NotImplementedError