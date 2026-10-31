"""Provider registry and refresh-target resolution."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable

from app.core.config import Settings
from app.core.errors import BadRequestError
from app.sources.base import SourceAdapter


class SourceRegistry:
    def __init__(self, adapters: Iterable[SourceAdapter]) -> None:
        self._adapters: OrderedDict[str, SourceAdapter] = OrderedDict(
            (adapter.key, adapter) for adapter in adapters
        )

    def all(self) -> list[SourceAdapter]:
        return list(self._adapters.values())

    def keys(self) -> list[str]:
        return list(self._adapters)

    def get(self, key: str) -> SourceAdapter | None:
        return self._adapters.get(key)

    def require(self, key: str) -> SourceAdapter:
        adapter = self.get(key)
        if adapter is None:
            raise BadRequestError(f"Unknown job source: {key!r}")
        return adapter

    def enabled(self, configured_keys: Iterable[str] | None = None) -> list[SourceAdapter]:
        """Adapters allowed by configuration (empty config = everything)."""
        allowed = {key for key in (configured_keys or []) if key}
        adapters = self.all()
        if not allowed:
            return adapters
        unknown = allowed.difference(self._adapters)
        if unknown:
            raise BadRequestError(
                f"ENABLED_SOURCES contains unknown source(s): {', '.join(sorted(unknown))}"
            )
        return [adapter for adapter in adapters if adapter.key in allowed]

    def refresh_targets(
        self, requested: Iterable[str] | None, configured_keys: Iterable[str] | None = None
    ) -> list[SourceAdapter]:
        """Resolve which adapters a refresh run should attempt.

        Explicitly requested sources are returned even when unavailable so the
        run history records *why* nothing was imported. Automatic/scheduled
        refreshes only touch sources that can actually refresh, and never load
        the bundled sample feed: synthetic rows are a deliberate action, not a
        side effect of "refresh everything".
        """
        enabled = self.enabled(configured_keys)
        if requested:
            requested_list = [key for key in requested if key]
            if not requested_list:
                return []
            return [self.require(key) for key in requested_list]
        return [
            adapter for adapter in enabled if adapter.can_refresh and not adapter.is_test_data
        ]

    def known_keys(self) -> set[str]:
        return set(self._adapters)


def build_registry(settings: Settings) -> SourceRegistry:
    """Construct the registry, respecting ``ENABLED_SOURCES``."""
    from app.sources.fixtures import FixtureSourceAdapter
    from app.sources.indeed import IndeedSourceAdapter
    from app.sources.linkedin import LinkedInSourceAdapter
    from app.sources.manual_import import ManualImportSourceAdapter

    registry = SourceRegistry(
        [
            LinkedInSourceAdapter(settings),
            IndeedSourceAdapter(settings),
            ManualImportSourceAdapter(),
            FixtureSourceAdapter(),
        ]
    )
    # Fail fast on typos in ENABLED_SOURCES at startup.
    registry.enabled(settings.enabled_sources)
    return registry
