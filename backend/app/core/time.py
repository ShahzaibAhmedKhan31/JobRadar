"""Timezone helpers.

Every timestamp in JobRadar is stored as an aware UTC datetime. SQLite (used
by some test runs) drops tzinfo on round-trip, so read paths go through
``ensure_utc`` to normalize.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta


def utcnow() -> datetime:
    """Current time as an aware UTC datetime with second precision."""
    return datetime.now(UTC).replace(microsecond=0)


def ensure_utc(value: datetime | None) -> datetime | None:
    """Return ``value`` normalized to aware UTC (naive values assumed UTC)."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_iso_datetime(value: str | datetime | None) -> datetime | None:
    """Parse an ISO-8601 string (``Z`` suffix supported) to aware UTC."""
    if value is None or isinstance(value, datetime):
        return ensure_utc(value)
    text = value.strip()
    if not text:
        return None
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        return ensure_utc(datetime.fromisoformat(text))
    except ValueError as exc:  # pragma: no cover - message asserted in tests
        raise ValueError(f"Invalid ISO-8601 timestamp: {value!r}") from exc


def hours_since(value: datetime, now: datetime | None = None) -> float:
    reference = ensure_utc(value)
    now = ensure_utc(now) or utcnow()
    if reference is None:  # pragma: no cover - defensive
        raise ValueError("hours_since requires a datetime")
    return (now - reference).total_seconds() / 3600.0


def date_range_days(end: date, days: int) -> list[date]:
    """Ascending list of ``days`` dates ending at ``end`` (inclusive)."""
    if days < 1:
        raise ValueError("days must be >= 1")
    return [end - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
