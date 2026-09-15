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










@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

#  uv run python -c "from backend.app.core.config import settings; print(settings.app_name); print(settings.chunk_size)" 