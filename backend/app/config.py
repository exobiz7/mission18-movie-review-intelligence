"""Environment-configured settings with public-deployment fail-closed guardrails."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./.local/movie.db"
    backend_host: str = "127.0.0.1"
    backend_port: int = Field(default=8000, ge=1, le=65535)
    api_base_url: str = "http://127.0.0.1:8000"
    cors_allow_origins: str = "http://127.0.0.1:8518"
    model_backend: str = "unconfigured"
    model_path: str = ".local/models/koelectra-small-v3-nsmc"
    model_onnx_path: str = ".local/benchmark/onnx/koelectra-fp32.onnx"
    model_id: str = "daekeun-ml/koelectra-small-v3-nsmc"
    model_revision: str = "d1c0233fc013ae8bd879d7b61f2bec69aa3af4c9"
    max_tokens: int = Field(default=192, ge=8, le=512)
    public_deployment: bool = False
    write_policy: Literal["loopback", "read_only", "token", "public_demo"] = "loopback"
    public_demo_acknowledged: bool = False
    demo_writes_per_minute: int = Field(default=60, ge=10, le=300)
    api_write_token: SecretStr | None = None

    @property
    def allowed_origins(self) -> list[str]:
        return [part.strip() for part in self.cors_allow_origins.split(",") if part.strip()]

    @model_validator(mode="after")
    def fail_closed_public_configuration(self) -> Settings:
        if self.write_policy == "public_demo" and not self.public_demo_acknowledged:
            raise ValueError("Public demo writes require explicit PUBLIC_DEMO_ACKNOWLEDGED=true")
        if self.write_policy == "token":
            token = self.api_write_token.get_secret_value() if self.api_write_token else ""
            if (
                len(token.encode("utf-8")) < 32
                or len(set(token)) < 8
                or any(ch.isspace() for ch in token)
            ):
                raise ValueError("Token policy requires a strong non-whitespace API_WRITE_TOKEN")
        if self.public_deployment:
            if self.write_policy == "loopback":
                raise ValueError("Public deployment must use read_only or token write policy")
            if not self.database_url.startswith("postgresql"):
                raise ValueError("Public deployment requires a persistent PostgreSQL URL")
            origins = self.allowed_origins
            if not origins:
                raise ValueError("Public deployment requires explicit HTTPS CORS origins")
            for origin in origins:
                parsed = urlsplit(origin)
                if (
                    parsed.scheme != "https"
                    or not parsed.hostname
                    or parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                    or parsed.path not in ("", "/")
                    or "*" in origin
                ):
                    raise ValueError("Public deployment requires exact HTTPS CORS origins")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
