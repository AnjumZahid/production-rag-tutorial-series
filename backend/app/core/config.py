from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

class Settings(BaseSettings):
    app_name: str = "Production RAG API"
    app_environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    chunk_size: int = Field(default=1000, ge=100, le=5000)
    chunk_overlap: int = Field(default=200, ge=0, le=1000)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    embedding_batch_size: int = Field(default=32, ge=1, le=512)
    embedding_normalize: bool = True
    
      
    embedding_provider: str = "huggingface"

    # # ===========================================================
    # # Settings for openAI embdeddings generation
    # # ===========================================================

    # # OpenAI authentication and model.
    # openai_api_key: SecretStr | None = None
    # openai_embedding_model: str = "text-embedding-3-small"

    # # Optional reduced vector dimension.
    # # Keep None to use the model's default dimension.
    # openai_embedding_dimensions: int | None = Field(
    #     default=None,
    #     ge=1,
    # )

    # # Maximum number of texts sent in one request.
    # openai_embedding_batch_size: int = Field(
    #     default=64,
    #     ge=1,
    #     le=2048,
    # )

    # # Safety limits below OpenAI's official maximums.
    # openai_embedding_max_input_tokens: int = Field(
    #     default=8000,
    #     ge=1,
    #     le=8192,
    # )

    # openai_embedding_max_batch_tokens: int = Field(
    #     default=250_000,
    #     ge=1,
    #     le=300_000,
    # )

    # # Retry configuration.
    # openai_embedding_max_retries: int = Field(
    #     default=6,
    #     ge=0,
    #     le=10,
    # )

    # openai_embedding_initial_retry_delay: float = Field(
    #     default=1.0,
    #     ge=0.1,
    #     le=60,
    # )

    # openai_embedding_max_retry_delay: float = Field(
    #     default=60.0,
    #     ge=1,
    #     le=300,
    # )

    # # Small delay between successful batches.
    # openai_embedding_batch_delay: float = Field(
    #     default=0.25,
    #     ge=0,
    #     le=60,
    # )

    # openai_timeout_seconds: float = Field(
    #     default=60.0,
    #     ge=1,
    #     le=600,
    # )


# =======================================

    # Select which vector database provider the application uses.

    vector_store_provider: Literal["chroma", "qdrant"] = "chroma"

    # Local directory where persistent Chroma data is stored.
    chroma_persist_directory: str = "./data/chroma"

    # Database created inside every organization-specific Chroma tenant.
    chroma_database_name: str = "rag_app"

    # Default number of relevant chunks returned during retrieval.
    retrieval_top_k: int = Field(
        default=4,
        ge=1,
        le=50,
    )

# ===========================================

    # MySQL connection configuration.
    database_url: SecretStr | None = None

    database_echo: bool = False

    database_pool_size: int = Field(
        default=10,
        ge=1,
        le=100,
    )

    database_max_overflow: int = Field(
        default=20,
        ge=0,
        le=200,
    )

    database_pool_recycle_seconds: int = Field(
        default=1800,
        ge=60,
    )

    # ===============================


    # ===========================================================
    # LLM provider configuration
    # ===========================================================

    llm_provider: Literal["openai", "gemini"] = "gemini"

    # ===========================================================
    # OpenAI LLM configuration
    # ===========================================================

    openai_llm_model: str = "gpt-5.4-mini"

    openai_llm_timeout_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
    )

    openai_llm_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    openai_llm_max_output_tokens: int = Field(
        default=1200,
        ge=64,
        le=20_000,
    )

    openai_llm_reasoning_effort: Literal[
        "none",
        "low",
        "medium",
        "high",
    ] = "low"

    # ===========================================================
    # Google Gemini LLM configuration
    # ===========================================================

    gemini_api_key: SecretStr | None = None

    gemini_llm_model: str = "gemini-2.5-flash"

    gemini_llm_timeout_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=600.0,
    )

    gemini_llm_max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
    )

    gemini_llm_initial_retry_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
    )

    gemini_llm_max_retry_delay_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
    )

    gemini_llm_max_output_tokens: int = Field(
        default=1200,
        ge=64,
        le=65_536,
    )

    gemini_llm_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
    )

    gemini_llm_thinking_budget: int = Field(
        default=0,
        ge=-1,
    )





@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

#  uv run python -c "from backend.app.core.config import settings; print(settings.app_name); print(settings.chunk_size)" 