"""Record a listing the user found on a job board themselves.

This is *not* an automated integration: the user supplies every field. It keeps
LinkedIn/Indeed links useful even though those platforms cannot be legally
scraped or do not expose a public search API.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.errors import BadRequestError, UnprocessableError
from app.models.job import Job
from app.schemas.job import ManualJobImport
from app.services.ingestion import (
    InvalidJobPayload,
    find_existing_job,
    sanitize_job,
    upsert_job,
)
from app.sources.base import NormalizedJob
from app.sources.manual_import import MANUAL_IMPORT_SOURCES


def import_job(db: Session, payload: ManualJobImport) -> tuple[Job, bool]:
    if payload.source not in MANUAL_IMPORT_SOURCES:
        raise BadRequestError(
            "Manual imports can be attributed to: " + ", ".join(MANUAL_IMPORT_SOURCES)
        )

    item = NormalizedJob(
        title=payload.title,
        company_name=payload.company_name,
        job_url=payload.job_url,
        source_job_id=payload.source_job_id,
        location=payload.location,
        work_arrangement=payload.work_arrangement,
        experience_level=payload.experience_level,
        description=payload.description,
        published_at=payload.published_at,
    )
    try:
        clean = sanitize_job(item)
    except InvalidJobPayload as exc:
        raise UnprocessableError(str(exc)) from exc

    existing = find_existing_job(db, payload.source, clean)
    if existing is not None:
        return existing, False

    try:
        outcome = upsert_job(
            db, source=payload.source, item=clean, is_test_data=False
        )
    except InvalidJobPayload as exc:  # pragma: no cover - validated above
        raise UnprocessableError(str(exc)) from exc
    db.commit()
    db.refresh(outcome.job)
    return outcome.job, True
