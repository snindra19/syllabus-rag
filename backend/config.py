"""Application settings loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config — all values come from .env or environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    anthropic_api_key: str
    openai_api_key: str

    # Database
    database_url: str

    # Model selection (override in .env to upgrade)
    chat_model: str = "claude-haiku-4-5-20251001"
    preprocessing_model: str = "claude-haiku-4-5-20251001"
    embedding_model: str = "text-embedding-3-small"

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
