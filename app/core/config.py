"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Gold Queen API"
    environment: str = "development"
    # Kept as a raw string: pydantic-settings would try to JSON-decode a list field
    # before any validator runs, which rejects the comma-separated form.
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    database_url: str = "sqlite:///./gold_queen.db"

    jwt_secret: str = "change-me-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    pluggy_client_id: str = ""
    pluggy_client_secret: str = ""
    pluggy_base_url: str = "https://api.pluggy.ai"

    gemini_api_key: str = ""
    # The PRD specified gemini-1.5-flash, which Google has since retired; 2.5-flash
    # is also closed to new API keys. 3.6-flash is the current flash tier.
    gemini_model: str = "gemini-3.6-flash"

    max_bank_connections: int = 3
    chat_daily_limit: int = 10

    @field_validator("database_url", mode="before")
    @classmethod
    def fallback_to_sqlite(cls, value: object) -> object:
        if not value:
            return "sqlite:///./gold_queen.db"
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def pluggy_enabled(self) -> bool:
        return bool(self.pluggy_client_id and self.pluggy_client_secret)

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
