"""Job source adapters (one module per provider)."""

from app.sources.base import (
    FetchResult,
    JobQuery,
    NormalizedJob,
    SourceAdapter,
    SourceRequestError,
    SourceUnavailableError,
)
from app.sources.registry import SourceRegistry, build_registry

__all__ = [
    "FetchResult",
    "JobQuery",
    "NormalizedJob",
    "SourceAdapter",
    "SourceRegistry",
    "SourceRequestError",
    "SourceUnavailableError",
    "build_registry",
]
