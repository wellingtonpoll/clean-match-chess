"""SQLAlchemy declarative models for the analysis cache + baseline persistence.

Feature 008 (audit_runs) + feature 007 (baseline_runs/pgn_corpus/baseline_samples/
baseline_analyses). Models are kept in lockstep with the migration files
manually — no autogenerate.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base shared by every model in this package."""


class AuditRunModel(Base):
    """One persisted `AuditRun` per `(pgn_sha256, manifest_sha256)`.

    Cache lookups use the composite UNIQUE constraint; future feature 009+
    queries hit the `(white_username)` / `(black_username)` / `(created_at
    DESC)` indexes for history pages and per-user analytics.
    """

    __tablename__ = "audit_runs"
    __table_args__ = (
        UniqueConstraint("pgn_sha256", "manifest_sha256", name="audit_runs_pgn_manifest_unique"),
        Index("idx_audit_runs_platform_game", "platform", "game_id"),
        Index("idx_audit_runs_white", "white_username"),
        Index("idx_audit_runs_black", "black_username"),
        Index("idx_audit_runs_created", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    pgn_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    manifest_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)

    platform: Mapped[str | None] = mapped_column(String(16), nullable=True)
    game_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    white_username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    black_username: Mapped[str | None] = mapped_column(String(64), nullable=True)

    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    run_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Reserved nullable columns for the upcoming auth + multi-tenancy
    # feature (009+). No FK constraints yet — added by a future
    # migration once `users` and `tenants` tables land.
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class BaselineRunModel(Base):
    """One Stockfish-baseline build pass (feature 007).

    Mirrors `migrations/versions/0002_baseline_persistence.py`. A row is
    inserted at script start with `status='running'`, updated as Phase 1
    streams + Phase 2 analyses progress, and closed with status
    'completed' / 'failed' / 'aborted'.
    """

    __tablename__ = "baseline_runs"
    __table_args__ = (
        CheckConstraint(
            "octet_length(archive_sha256) = 32",
            name="baseline_runs_archive_sha256_length",
        ),
        CheckConstraint(
            "octet_length(engine_binary_sha256) = 32",
            name="baseline_runs_engine_sha256_length",
        ),
        CheckConstraint("per_bucket_sample > 0", name="baseline_runs_per_bucket_positive"),
        CheckConstraint("depth > 0", name="baseline_runs_depth_positive"),
        CheckConstraint("multipv > 0", name="baseline_runs_multipv_positive"),
        CheckConstraint("workers > 0", name="baseline_runs_workers_positive"),
        CheckConstraint(
            "status IN ('running','completed','failed','aborted')",
            name="baseline_runs_status_check",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="baseline_runs_time_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    archive_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    source_dataset: Mapped[str] = mapped_column(String(128), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    per_bucket_sample: Mapped[int] = mapped_column(Integer, nullable=False)
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    multipv: Mapped[int] = mapped_column(Integer, nullable=False)
    workers: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_binary_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    script_version: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'running'"),
    )
    total_scanned: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_sampled: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    total_analysed: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class PgnCorpusModel(Base):
    """Deduplicated PGN store keyed by sha256."""

    __tablename__ = "pgn_corpus"
    __table_args__ = (
        CheckConstraint("octet_length(pgn_sha256) = 32", name="pgn_corpus_sha256_length"),
    )

    pgn_sha256: Mapped[bytes] = mapped_column(LargeBinary, primary_key=True)
    pgn_text: Mapped[str] = mapped_column(Text, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class BaselineSampleModel(Base):
    """One sampled game per (run, bucket, reservoir position).

    The (run_id, bucket_label, reservoir_position) tuple is unique —
    Algorithm-L overwrites a slot via upsert. Workers in Phase 2 claim
    rows via `SELECT FOR UPDATE SKIP LOCKED` using
    `idx_baseline_samples_pending` (partial index on analysed=FALSE).
    """

    __tablename__ = "baseline_samples"
    __table_args__ = (
        ForeignKeyConstraint(
            ["pgn_sha256"],
            ["pgn_corpus.pgn_sha256"],
            name="baseline_samples_pgn_fk",
            deferrable=True,
            initially="DEFERRED",
        ),
        UniqueConstraint(
            "run_id",
            "bucket_label",
            "reservoir_position",
            name="baseline_samples_position_unique",
        ),
        CheckConstraint(
            "white_elo IS NULL OR white_elo BETWEEN 600 AND 3500",
            name="baseline_samples_white_elo_range",
        ),
        CheckConstraint(
            "black_elo IS NULL OR black_elo BETWEEN 600 AND 3500",
            name="baseline_samples_black_elo_range",
        ),
        CheckConstraint(
            "ply_count IS NULL OR ply_count >= 0",
            name="baseline_samples_ply_count_nonneg",
        ),
        CheckConstraint(
            "reservoir_position >= 0",
            name="baseline_samples_position_nonneg",
        ),
        CheckConstraint(
            "bucket_label IN ('≤1200','1201-1500','1501-1800','1801-2100','2101-2400','2401+')",
            name="baseline_samples_bucket_check",
        ),
        Index(
            "idx_baseline_samples_pending",
            "run_id",
            text("claimed_at NULLS FIRST"),
            postgresql_where=text("analysed = FALSE"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("baseline_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    bucket_label: Mapped[str] = mapped_column(String(16), nullable=False)
    pgn_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    white_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    black_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)
    time_control: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ply_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reservoir_position: Mapped[int] = mapped_column(Integer, nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    analysed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("FALSE"),
    )


class BaselineAnalysisModel(Base):
    """One Stockfish analysis result per baseline sample.

    INSERT fires `trg_mark_sample_analysed` which UPDATEs
    `baseline_samples.analysed = TRUE` for the sample_id.
    """

    __tablename__ = "baseline_analyses"
    __table_args__ = (
        UniqueConstraint("sample_id", name="baseline_analyses_sample_unique"),
        CheckConstraint(
            "top1_rate BETWEEN 0 AND 1",
            name="baseline_analyses_top1_rate_range",
        ),
        CheckConstraint(
            "weighted_rate BETWEEN 0 AND 1",
            name="baseline_analyses_weighted_rate_range",
        ),
        CheckConstraint("acpl >= 0", name="baseline_analyses_acpl_nonneg"),
        CheckConstraint(
            "eligible_plies >= 0",
            name="baseline_analyses_eligible_plies_nonneg",
        ),
        CheckConstraint(
            "analysis_duration_ms IS NULL OR analysis_duration_ms >= 0",
            name="baseline_analyses_duration_nonneg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    sample_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("baseline_samples.id", ondelete="CASCADE"),
        nullable=False,
    )
    top1_rate: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    weighted_rate: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    acpl: Mapped[float] = mapped_column(Float(precision=53), nullable=False)
    eligible_plies: Mapped[int] = mapped_column(Integer, nullable=False)
    analysed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    analysis_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditJobModel(Base):
    """One audit job in the async queue (feature 011 Phase 3).

    Mirrors `migrations/versions/0003_audit_jobs.py`. The frontend
    `POST /api/audit` inserts a row with status='queued'; a Postgres
    trigger fires `NOTIFY audit_jobs_new`. The worker daemon LISTENs on
    that channel, claims via SELECT FOR UPDATE SKIP LOCKED, runs the
    audit pipeline, and updates status='completed'/'failed' — the
    second trigger fires `NOTIFY audit_jobs_done`.
    """

    __tablename__ = "audit_jobs"
    __table_args__ = (
        CheckConstraint(
            "octet_length(pgn_sha256) = 32",
            name="audit_jobs_pgn_sha256_length",
        ),
        CheckConstraint(
            "subject_color IN ('white', 'black')",
            name="audit_jobs_subject_color_check",
        ),
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'aborted')",
            name="audit_jobs_status_check",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= created_at",
            name="audit_jobs_time_check",
        ),
        Index(
            "idx_audit_jobs_pending",
            "created_at",
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    pgn_text: Mapped[str] = mapped_column(Text, nullable=False)
    pgn_sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    subject_color: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        server_default=text("'queued'"),
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    audit_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
