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
    #: Compare the database's alembic revision with the code before serving.
    schema_check_on_startup: bool = True
    #: Apply pending migrations automatically instead of refusing to start.
    schema_auto_upgrade: bool = False
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

    # Scraping (python-jobspy) ------------------------------------------------
    #: Global kill switch for the optional python-jobspy adapter.
    jobspy_enabled: bool = True
    #: Which jobspy sites may be scraped. ``linkedin`` is the default; add
    #: ``indeed`` (or ``glassdoor``/``zip_recruiter``/``bayt``/``naukri``) to
    #: opt in. Sites are only scraped when they are also listed here *and* the
    #: python-jobspy package is installed.
    jobspy_sites: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["linkedin"]
    )
    #: Listings requested per search term (jobspy ``results_wanted``).
    jobspy_results_wanted: int = Field(default=25, ge=1, le=200)
    #: How many of the configured titles/keywords are sent to the provider.
    #: Each term is a separate HTTP request, so keep this small.
    jobspy_max_search_terms: int = Field(default=3, ge=1, le=5)
    #: Minimum delay between two scrape requests (politeness / rate limiting).
    jobspy_request_delay_seconds: float = Field(default=2.0, ge=0, le=60)
    #: Optional HTTP(S) proxies, comma separated, rotated by jobspy.
    jobspy_proxies: Annotated[list[str], NoDecode] = Field(default_factory=list)
    #: Country hint for the Indeed scraper (ignored for LinkedIn).
    jobspy_country: str = "pakistan"
    #: Fallback search location when neither the refresh request nor the saved
    #: Search Settings carry one. Without this, LinkedIn answers with a US-wide
    #: feed, which is how unrelated listings end up in the database.
    #: Empty means "use the country above" (e.g. ``pakistan`` -> ``Pakistan``).
    jobspy_default_location: str = ""
    #: Fetch full descriptions. One extra request per listing on LinkedIn, so
    #: this multiplies traffic and raises the throttling risk.
    jobspy_fetch_description: bool = False
    #: jobspy log verbosity: 0 quiet, 1 default, 2 debug.
    jobspy_verbose: int = Field(default=0, ge=0, le=2)

    @field_validator(
        "cors_origins", "enabled_sources", "jobspy_sites", "jobspy_proxies", mode="before"
    )
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

    @field_validator("jobspy_sites")
    @classmethod
    def _normalise_sites(cls, value: list[str]) -> list[str]:
        allowed = {"linkedin", "indeed", "glassdoor", "zip_recruiter", "bayt", "naukri"}
        cleaned: list[str] = []
        for item in value:
            site = item.strip().lower()
            if not site or site in cleaned:
                continue
            if site not in allowed:
                raise ValueError(
                    f"Unsupported jobspy site {site!r}. Supported: {', '.join(sorted(allowed))}"
                )
            cleaned.append(site)
        return cleaned

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
