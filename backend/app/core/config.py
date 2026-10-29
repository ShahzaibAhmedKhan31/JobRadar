"""Application configuration loaded from environment variables / ``.env``."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "JobRadar API"
    app_version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # Database ---------------------------------------------------------------
    database_url: str = (
        "postgresql+psycopg://jobradar:jobradar@localhost:5432/jobradar"
    )
    db_wait_on_startup: bool = True
    db_wait_attempts: int = Field(default=30, ge=1, le=600)
    db_wait_interval_seconds: float = Field(default=2.0, ge=0.1, le=30)

    # HTTP -------------------------------------------------------------------
    api_prefix: str = "/api"
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )

    # Pagination / limits ----------------------------------------------------
    max_page_size: int = Field(default=100, ge=1, le=500)
    max_refresh_jobs_per_source: int = Field(default=500, ge=1, le=5000)

    # Ingestion --------------------------------------------------------------
    #: Optional allow-list of provider keys, e.g. ``fixtures,manual_import``.
    enabled_sources: Annotated[list[str], NoDecode] = Field(default_factory=list)

    #: Seeds the "automatic refresh" toggle in Search Settings.
    scheduled_refresh_enabled: bool = False
    scheduled_refresh_interval_minutes: int = Field(default=60, ge=15, le=1440)
    #: Master switch for the in-process scheduler loop (useful for tests).
    scheduler_enabled: bool = True
    scheduler_tick_seconds: int = Field(default=30, ge=5, le=300)

    @field_validator("cors_origins", "enabled_sources", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        """Allow ``A,B`` as well as JSON arrays in environment variables."""
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                return value
            return [item.strip() for item in text.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def _strip_trailing_slash(cls, value: list[str]) -> list[str]:
        return [origin.rstrip("/") for origin in value]

    @field_validator("database_url")
    @classmethod
    def _forbid_async_pg_driver(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned.startswith("postgresql+asyncpg"):
            # The app is fully synchronous; keep the error message actionable.
            raise ValueError(
                "Use a synchronous PostgreSQL driver, e.g. "
                "postgresql+psycopg://user:pass@localhost:5432/jobradar"
            )
        return cleaned

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()
