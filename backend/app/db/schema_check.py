"""Schema version checks.

A stale database is the most common way to get a confusing 500 out of JobRadar:
the code ships a new column, the developer pulls it, and the running Postgres
still has yesterday's tables. This module compares the revision stored in
``alembic_version`` with the head revision in ``backend/alembic/versions`` and
turns that mismatch into an explicit, actionable startup error instead of a
traceback buried in a request.

Behaviour
---------
* Database at head            → fine.
* Database behind/ahead       → startup fails with the exact command to run,
  unless ``SCHEMA_AUTO_UPGRADE=true`` (then ``alembic upgrade head`` runs first).
* No ``alembic_version`` table → warning only. Fresh databases and the test
  fixture create tables from metadata without stamping a revision.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
ALEMBIC_DIR = BACKEND_DIR / "alembic"

UPGRADE_COMMAND = "alembic upgrade head"


class SchemaState(StrEnum):
    AT_HEAD = "at_head"
    STALE = "stale"
    UNINITIALIZED = "uninitialized"
    UNKNOWN = "unknown"


@dataclass(slots=True)
class SchemaStatus:
    state: SchemaState
    current: str | None = None
    head: str | None = None
    detail: str | None = None

    @property
    def is_stale(self) -> bool:
        return self.state is SchemaState.STALE

    def describe(self) -> str:
        if self.state is SchemaState.AT_HEAD:
            return f"database schema is at head ({self.current})"
        if self.state is SchemaState.STALE:
            direction = "behind" if self._is_behind() else "ahead of"
            return (
                f"database schema is {direction} the code: database at "
                f"{self.current or 'unknown'}, code expects {self.head}. "
                f"Run `{UPGRADE_COMMAND}` from backend/."
            )
        if self.state is SchemaState.UNINITIALIZED:
            return (
                "no alembic_version table found — migrations have not been applied. "
                f"Run `{UPGRADE_COMMAND}` from backend/."
            )
        return f"could not determine schema version: {self.detail}"

    def _is_behind(self) -> bool:
        # Alembic revisions are not ordered numerically; without walking the
        # migration graph the safest phrasing is "different from the code".
        return True


def head_revision() -> str | None:
    """Newest revision known to the code, or ``None`` if unavailable."""
    try:
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(ALEMBIC_DIR))
        return ScriptDirectory.from_config(config).get_current_head()
    except Exception as exc:
        logger.debug("Could not read the Alembic head revision: %s", exc)
        return None


def current_revision(engine: Engine) -> tuple[str | None, bool]:
    """Return ``(revision, table_exists)`` for the connected database."""
    try:
        with engine.connect() as connection:
            exists = connection.execute(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            ).scalar()
            if not exists:
                return None, False
            revision = connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one_or_none()
            return (str(revision) if revision else None), True
    except SQLAlchemyError as exc:
        logger.debug("Could not read alembic_version: %s", exc)
        return None, False


def schema_status(engine: Engine) -> SchemaStatus:
    head = head_revision()
    current, table_exists = current_revision(engine)
    if not table_exists:
        return SchemaStatus(SchemaState.UNINITIALIZED, current=None, head=head)
    if head is None:
        return SchemaStatus(
            SchemaState.UNKNOWN,
            current=current,
            head=None,
            detail="alembic.ini or the versions directory is not readable",
        )
    if current == head:
        return SchemaStatus(SchemaState.AT_HEAD, current=current, head=head)
    return SchemaStatus(SchemaState.STALE, current=current, head=head)


def upgrade_to_head() -> None:
    """Apply every pending migration (used only when explicitly enabled)."""
    from alembic.config import Config

    from alembic import command

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    logger.warning("Applying pending migrations because SCHEMA_AUTO_UPGRADE=true")
    command.upgrade(config, "head")


def ensure_schema(engine: Engine, settings: Settings) -> SchemaStatus:
    """Verify (and optionally migrate) the schema before serving requests.

    Raises:
        RuntimeError: when the schema is stale and auto-upgrade is disabled, so
            uvicorn prints the instruction instead of every endpoint failing.
    """
    if settings.is_sqlite or not settings.schema_check_on_startup:
        return SchemaStatus(SchemaState.UNKNOWN, detail="check disabled")

    status = schema_status(engine)
    if status.is_stale:
        if settings.schema_auto_upgrade:
            upgrade_to_head()
            status = schema_status(engine)
            if status.state is SchemaState.AT_HEAD:
                logger.warning("Database migrated to %s at startup", status.current)
                return status
        logger.critical("%s", status.describe())
        raise RuntimeError(
            f"Database schema does not match the code. {status.describe()} "
            "Set SCHEMA_AUTO_UPGRADE=true to let the API migrate on startup instead."
        )
    if status.state is SchemaState.UNINITIALIZED:
        logger.warning("%s", status.describe())
    elif status.state is SchemaState.UNKNOWN:
        logger.debug("%s", status.describe())
    else:
        logger.info("Schema version %s", status.current)
    return status
