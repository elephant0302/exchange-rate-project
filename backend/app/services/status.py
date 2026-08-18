from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CollectionStatus
from app.services.normalize import utcnow


def upsert_status(
    db: Session,
    job_name: str,
    status: str,
    source: str = "",
    message: str = "",
    is_mock: bool = False,
    success: bool = False,
    at: datetime | None = None,
) -> CollectionStatus:
    at = at or utcnow()
    row = db.get(CollectionStatus, job_name)
    if row is None:
        row = CollectionStatus(job_name=job_name)
        db.add(row)
    row.status = status
    row.source = source
    row.message = message
    row.is_mock = is_mock
    row.last_run_at = at
    if success:
        row.last_success_at = at
    db.commit()
    db.refresh(row)
    return row


def list_statuses(db: Session) -> list[CollectionStatus]:
    return list(db.scalars(select(CollectionStatus)).all())
