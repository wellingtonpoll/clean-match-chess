"""Repository for the async audit job queue (feature 011 Phase 3).

Backs the worker daemon at `apps/frontend/lib/audit_worker.py` and the
two Next.js API routes (`POST /api/audit`, `GET /api/audit/[job_id]`).
All DB writes flow through this module so the SQL stays auditable + the
worker logic stays orchestration-only.

Functions raise on errors (this is a maintainer-grade infrastructure
layer, not a graceful-degrade cache like `db.cache`). Worker daemon
catches and marks the job `failed` rather than crashing.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from analysis_core.db.models import AuditJobModel

_STALE_CLAIM_MINUTES = 15


@dataclass(frozen=True)
class ClaimedJob:
    """Result of `claim_next_job()` — ready for the worker to process."""

    job_id: uuid.UUID
    pgn_text: str
    pgn_sha256: bytes
    subject_color: str


@dataclass(frozen=True)
class JobStatus:
    """Snapshot of a job's state for the frontend status endpoint."""

    job_id: uuid.UUID
    status: str
    result_json: dict[str, Any] | None
    error_message: str | None
    audit_run_id: uuid.UUID | None


def enqueue(
    session: Session,
    *,
    pgn_text: str,
    subject_color: str = "white",
) -> uuid.UUID:
    """Insert one row into `audit_jobs` (status='queued'). Returns the job id.

    The trigger `trg_notify_audit_job_new` fires on commit, so any
    LISTEN'er on `audit_jobs_new` wakes up.
    """
    if subject_color not in ("white", "black"):
        raise ValueError(f"subject_color must be 'white' or 'black'; got {subject_color!r}")
    pgn_sha = hashlib.sha256(pgn_text.encode("utf-8")).digest()
    job = AuditJobModel(
        pgn_text=pgn_text,
        pgn_sha256=pgn_sha,
        subject_color=subject_color,
    )
    session.add(job)
    session.flush()
    return job.id


def claim_next_job(
    session: Session,
    *,
    stale_threshold_minutes: int = _STALE_CLAIM_MINUTES,
) -> ClaimedJob | None:
    """Atomically claim the oldest queued (or stale-running) job.

    Uses `SELECT FOR UPDATE SKIP LOCKED` so multiple worker processes
    can drain the queue without stepping on each other. Updates
    `status='running'`, `claimed_at=NOW()`, `started_at=NOW()` in the
    same transaction.

    Stale-running jobs (claimed_at older than `stale_threshold_minutes`)
    are eligible for re-claim — covers workers that crashed mid-analysis.
    """
    stmt = text(
        """
        SELECT id, pgn_text, pgn_sha256, subject_color
        FROM audit_jobs
        WHERE (status = 'queued')
           OR (status = 'running'
               AND claimed_at < NOW() - make_interval(mins => :stale))
        ORDER BY created_at ASC
        FOR UPDATE SKIP LOCKED
        LIMIT 1
        """
    )
    row = session.execute(stmt, {"stale": stale_threshold_minutes}).first()
    if row is None:
        return None
    session.execute(
        text(
            "UPDATE audit_jobs SET status = 'running', claimed_at = NOW(), "
            "started_at = COALESCE(started_at, NOW()) WHERE id = :id"
        ),
        {"id": row.id},
    )
    return ClaimedJob(
        job_id=row.id,
        pgn_text=row.pgn_text,
        pgn_sha256=bytes(row.pgn_sha256),
        subject_color=row.subject_color,
    )


def mark_completed(
    session: Session,
    *,
    job_id: uuid.UUID,
    result_json: dict[str, Any],
    audit_run_id: uuid.UUID | None = None,
) -> None:
    session.execute(
        update(AuditJobModel)
        .where(AuditJobModel.id == job_id)
        .values(
            status="completed",
            result_json=result_json,
            audit_run_id=audit_run_id,
            finished_at=text("NOW()"),
        )
    )


def mark_failed(
    session: Session,
    *,
    job_id: uuid.UUID,
    error_message: str,
    status: str = "failed",
) -> None:
    if status not in ("failed", "aborted"):
        raise ValueError(f"invalid terminal status: {status}")
    session.execute(
        update(AuditJobModel)
        .where(AuditJobModel.id == job_id)
        .values(
            status=status,
            error_message=error_message[:4000],
            finished_at=text("NOW()"),
        )
    )


def get_status(session: Session, *, job_id: uuid.UUID) -> JobStatus | None:
    """Frontend status poll. Returns None when job doesn't exist."""
    row = session.execute(
        select(
            AuditJobModel.id,
            AuditJobModel.status,
            AuditJobModel.result_json,
            AuditJobModel.error_message,
            AuditJobModel.audit_run_id,
        ).where(AuditJobModel.id == job_id)
    ).first()
    if row is None:
        return None
    return JobStatus(
        job_id=row.id,
        status=row.status,
        result_json=row.result_json,
        error_message=row.error_message,
        audit_run_id=row.audit_run_id,
    )
