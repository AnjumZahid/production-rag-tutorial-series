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

   
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

#  uv run python -c "from backend.app.core.config import settings; print(settings.app_name); print(settings.chunk_size)" 