from abc import ABC, abstractmethod


class BaseLLMProvider(ABC):
    """Common interface implemented by language-model providers."""

    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """Generate one text response."""