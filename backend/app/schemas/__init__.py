"""Pydantic schemas (API request/response contracts)."""

from app.schemas.application import (
    ApplicationCreate,
    ApplicationRead,
    ApplicationStatusColumn,
    ApplicationUpdate,
    application_to_read,
)
from app.schemas.common import Page
from app.schemas.dashboard import (
    ActivityPoint,
    ActivityResponse,
    DashboardSummary,
    SourceBreakdownItem,
    StatusBreakdownItem,
)
from app.schemas.job import (
    ApplicationSummary,
    DuplicateRef,
    JobDetail,
    JobPage,
    JobRead,
    ManualImportResponse,
    ManualJobImport,
    ShortlistSummary,
    job_to_read,
)
from app.schemas.refresh import (
    FetchRunRead,
    RefreshRequest,
    RefreshResponse,
    RefreshSourceResult,
    fetch_run_to_read,
)
from app.schemas.settings import SearchSettingsRead, SearchSettingsUpdate
from app.schemas.shortlist import (
    ShortlistCreate,
    ShortlistRead,
    ShortlistUpdate,
    shortlist_to_read,
)
from app.schemas.source import SourceRead, SourcesResponse

__all__ = [
    "ActivityPoint",
    "ActivityResponse",
    "ApplicationCreate",
    "ApplicationRead",
    "ApplicationStatusColumn",
    "ApplicationSummary",
    "ApplicationUpdate",
    "DashboardSummary",
    "DuplicateRef",
    "FetchRunRead",
    "JobDetail",
    "JobPage",
    "JobRead",
    "ManualImportResponse",
    "ManualJobImport",
    "Page",
    "RefreshRequest",
    "RefreshResponse",
    "RefreshSourceResult",
    "SearchSettingsRead",
    "SearchSettingsUpdate",
    "ShortlistCreate",
    "ShortlistRead",
    "ShortlistSummary",
    "ShortlistUpdate",
    "SourceBreakdownItem",
    "SourceRead",
    "SourcesResponse",
    "StatusBreakdownItem",
    "application_to_read",
    "fetch_run_to_read",
    "job_to_read",
    "shortlist_to_read",
]
