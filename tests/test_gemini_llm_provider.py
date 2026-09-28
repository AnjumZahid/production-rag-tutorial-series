from backend.app.core.exceptions import AppError
from backend.app.llms import (
    GeminiLLMProvider,
    get_llm_provider,
)


def main() -> None:
    provider = None

    try:
        provider = get_llm_provider()

        assert isinstance(
            provider,
            GeminiLLMProvider,
        )

        result = provider.generate(
            system_prompt=(
                "You are a concise test assistant. "
                "Follow the user's instruction exactly."
            ),
            user_prompt=(
                "Return exactly one short sentence confirming "
                "that the Gemini LLM provider works."
            ),
        )

        assert isinstance(result, str)
        assert result.strip()

        print("\n=== GEMINI LLM PROVIDER TEST ===")
        print("Provider:", type(provider).__name__)
        print("Model:", provider.model_name)
        print("Response:", result)
        print(
            "Gemini LLM provider test "
            "passed successfully."
        )

    except AppError as exc:
        print("\nGemini LLM provider test failed.")
        print("Code:", exc.code)
        print("Message:", exc.message)

        if exc.details:
            safe_details = dict(exc.details)
            safe_details.pop("api_key", None)

            print("Details:", safe_details)

        raise SystemExit(1) from exc

    finally:
        if provider is not None:
            close_method = getattr(
                provider,
                "close",
                None,
            )

            if callable(close_method):
                close_method()


if __name__ == "__main__":
    main()


# uv run python -m tests.test_gemini_llm_provider