"""Async audit job queue + LISTEN/NOTIFY triggers (feature 011 Phase 3).

Revision ID: 0003_audit_jobs
Revises: 0002_baseline_persistence
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0003_audit_jobs"
down_revision: str | Sequence[str] | None = "0002_baseline_persistence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_jobs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("pgn_text", sa.Text, nullable=False),
        sa.Column("pgn_sha256", sa.LargeBinary, nullable=False),
        sa.Column("subject_color", sa.String(8), nullable=False),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'queued'"),
        ),
        sa.Column("result_json", JSONB, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("audit_run_id", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "octet_length(pgn_sha256) = 32",
            name="audit_jobs_pgn_sha256_length",
        ),
        sa.CheckConstraint(
            "subject_color IN ('white', 'black')",
            name="audit_jobs_subject_color_check",
        ),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'aborted')",
            name="audit_jobs_status_check",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= created_at",
            name="audit_jobs_time_check",
        ),
    )

    # Partial index for the worker claim query (queued or stale-running rows).
    op.create_index(
        "idx_audit_jobs_pending",
        "audit_jobs",
        ["created_at"],
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )

    # NOTIFY on insert so the worker can wake up without polling.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_notify_audit_job_new()
        RETURNS TRIGGER AS $$
        BEGIN
          PERFORM pg_notify('audit_jobs_new', NEW.id::text);
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_notify_audit_job_new
        AFTER INSERT ON audit_jobs
        FOR EACH ROW EXECUTE FUNCTION fn_notify_audit_job_new();
        """
    )

    # NOTIFY on terminal status transition so the frontend can react.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_notify_audit_job_done()
        RETURNS TRIGGER AS $$
        BEGIN
          IF NEW.status IN ('completed', 'failed', 'aborted')
             AND (OLD.status IS DISTINCT FROM NEW.status) THEN
            PERFORM pg_notify('audit_jobs_done', NEW.id::text);
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_notify_audit_job_done
        AFTER UPDATE ON audit_jobs
        FOR EACH ROW EXECUTE FUNCTION fn_notify_audit_job_done();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_notify_audit_job_done ON audit_jobs")
    op.execute("DROP TRIGGER IF EXISTS trg_notify_audit_job_new ON audit_jobs")
    op.execute("DROP FUNCTION IF EXISTS fn_notify_audit_job_done()")
    op.execute("DROP FUNCTION IF EXISTS fn_notify_audit_job_new()")
    op.drop_index("idx_audit_jobs_pending", table_name="audit_jobs")
    op.drop_table("audit_jobs")
