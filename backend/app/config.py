"""Environment-based application settings (no host-specific hardcoding)."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./.local/movie.db"
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    api_base_url: str = "http://127.0.0.1:8000"
    cors_allow_origins: str = "http://127.0.0.1:8518"
    model_backend: str = "unconfigured"

    @property
    def allowed_origins(self) -> list[str]:
        return [part.strip() for part in self.cors_allow_origins.split(",") if part.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
