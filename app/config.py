"""Application configuration loaded from environment variables."""

from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./medara.db"

    # JWT
    secret_key: str = "changeme-super-secret-key-at-least-32-characters-long"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:8080",
        "https://medara-web.vercel.app",
    ]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                return [origin.strip() for origin in value.split(",")]
        return value

    # App metadata
    app_name: str = "MEDARA API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Security
    environment: str = "production"          # "production" ou "development"
    trusted_hosts: list[str] = ["*"]         # em prod: ["api.medara.com.br"]
    max_request_body_mb: int = 10            # limite de upload em MB

    # Agora.io (videochamadas)
    agora_app_id: str = ""
    agora_app_certificate: str = ""

    # Asaas (pagamentos)
    asaas_api_key: str = ""
    asaas_sandbox: bool = True

    @property
    def asaas_base_url(self) -> str:
        if self.asaas_sandbox:
            return "https://sandbox.asaas.com/api/v3"
        return "https://api.asaas.com/api/v3"


settings = Settings()
