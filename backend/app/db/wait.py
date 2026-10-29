"""Wait-for-database helper used during application startup."""

from __future__ import annotations

import time

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import ServiceUnavailableError
from app.core.logging import get_logger

logger = get_logger(__name__)


def wait_for_database(
    engine: Engine,
    *,
    attempts: int = 30,
    interval_seconds: float = 2.0,
) -> None:
    """Block until a trivial query succeeds, or raise a clear error.

    PostgreSQL in Docker can take a few seconds to accept connections on a cold
    start, so the API retries instead of crashing on boot.
    """
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            logger.info("Database connection established (attempt %s).", attempt)
            return
        except SQLAlchemyError as exc:  # pragma: no cover - timing dependent
            last_error = exc
            logger.warning(
                "Database not ready (attempt %s/%s): %s",
                attempt,
                attempts,
                str(exc).splitlines()[0][:200],
            )
            if attempt < attempts:
                time.sleep(interval_seconds)
    raise ServiceUnavailableError(
        "Could not connect to PostgreSQL after "
        f"{attempts} attempts. Is `docker compose up -d postgres` running? "
        f"Last error: {last_error}"
    )
