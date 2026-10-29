"""Source metadata combined with local import statistics."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.fetch_run import JobFetchRun
from app.models.job import Job
from app.schemas.refresh import fetch_run_to_read
from app.schemas.source import SourceRead, SourcesResponse
from app.sources.registry import SourceRegistry


def list_sources(db: Session, registry: SourceRegistry) -> SourcesResponse:
    job_counts = dict(
        db.execute(
            select(Job.source, func.count()).select_from(Job).group_by(Job.source)
        ).all()
    )

    latest_runs: dict[str, JobFetchRun] = {}
    runs = (
        db.execute(select(JobFetchRun).order_by(JobFetchRun.started_at.desc()).limit(200))
        .scalars()
        .all()
    )
    for run in runs:
        latest_runs.setdefault(run.source, run)

    sources: list[SourceRead] = []
    for descriptor in (adapter.describe() for adapter in registry.all()):
        key = str(descriptor["key"])
        sources.append(
            SourceRead(
                **descriptor,  # type: ignore[arg-type]
                stored_jobs_count=int(job_counts.get(key, 0)),
                last_run=(
                    fetch_run_to_read(latest_runs[key]) if key in latest_runs else None
                ),
            )
        )
    return SourcesResponse(sources=sources)
