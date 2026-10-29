"""Lightweight in-process scheduled refresh.

A single asyncio task ticks every ``SCHEDULER_TICK_SECONDS`` and triggers a
refresh when the persisted interval has elapsed. No external scheduler, queue or
worker process is required for a personal MVP.
"""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta

from app.core.config import Settings, get_settings
from app.core.constants import RefreshTrigger
from app.core.logging import get_logger
from app.core.time import ensure_utc, utcnow
from app.db.session import SessionLocal
from app.services.refresh import latest_scheduled_run_at, run_refresh
from app.services.search_settings import schedule_config
from app.sources.registry import SourceRegistry

logger = get_logger(__name__)


class RefreshScheduler:
    def __init__(self, registry: SourceRegistry, settings: Settings | None = None) -> None:
        self.registry = registry
        self.settings = settings or get_settings()
        self._task: asyncio.Task[None] | None = None
        self._started_at: datetime = utcnow()
        self._lock = asyncio.Lock()

    def start(self) -> None:
        if not self.settings.scheduler_enabled:
            logger.info("Background refresh scheduler disabled (SCHEDULER_ENABLED=false)")
            return
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._loop(), name="jobradar-refresh-scheduler")
        logger.info(
            "Background refresh scheduler started (tick=%ss)",
            self.settings.scheduler_tick_seconds,
        )

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        with suppress(asyncio.CancelledError):  # pragma: no cover - shutdown path
            await self._task
        self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.settings.scheduler_tick_seconds)
            try:
                await asyncio.to_thread(self.run_once)
            except Exception:  # pragma: no cover - defensive
                logger.exception("Scheduled refresh tick failed")

    def run_once(self) -> None:
        """Trigger a refresh if automatic refresh is enabled and due."""
        with SessionLocal() as db:
            enabled, interval_minutes = schedule_config(db, settings=self.settings)
            if not enabled:
                return
            if not any(adapter.can_refresh for adapter in self.registry.all()):
                return
            last_run = latest_scheduled_run_at(db) or ensure_utc(self._started_at)
            if last_run is not None and utcnow() - last_run < timedelta(
                minutes=interval_minutes
            ):
                return
            logger.info("Running scheduled refresh (interval=%s min)", interval_minutes)
            run_refresh(
                db,
                trigger=RefreshTrigger.SCHEDULED,
                registry=self.registry,
                settings=self.settings,
            )
