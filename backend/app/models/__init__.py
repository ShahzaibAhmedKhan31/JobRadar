"""Import every model so ``Base.metadata`` is complete (Alembic + tests)."""

from app.models.application import Application
from app.models.fetch_run import JobFetchRun
from app.models.job import Job
from app.models.search_settings import SINGLETON_ID, SearchSettings
from app.models.shortlist import ShortlistedJob

__all__ = [
    "SINGLETON_ID",
    "Application",
    "Job",
    "JobFetchRun",
    "SearchSettings",
    "ShortlistedJob",
]
