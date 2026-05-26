"""Baseline persistence schema — runs, samples, analyses, pgn corpus (feature 007).

Revision ID: 0002_baseline_persistence
Revises: 0001_init
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0002_baseline_persistence"
down_revision: str | Sequence[str] | None = "0001_init"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgcrypto extension already installed by 0001_init.

    op.create_table(
        "baseline_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("archive_sha256", sa.LargeBinary, nullable=False),
        sa.Column("source_dataset", sa.String(128), nullable=False),
        sa.Column("seed", sa.Integer, nullable=False),
        sa.Column("per_bucket_sample", sa.Integer, nullable=False),
        sa.Column("depth", sa.Integer, nullable=False),
        sa.Column("multipv", sa.Integer, nullable=False),
        sa.Column("workers", sa.Integer, nullable=False),
        sa.Column("engine_binary_sha256", sa.LargeBinary, nullable=False),
        sa.Column("script_version", sa.String(32), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        sa.Column("total_scanned", sa.BigInteger, nullable=True),
        sa.Column("total_sampled", sa.BigInteger, nullable=True),
        sa.Column(
            "total_analysed",
            sa.BigInteger,
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.CheckConstraint(
            "octet_length(archive_sha256) = 32",
            name="baseline_runs_archive_sha256_length",
        ),
        sa.CheckConstraint(
            "octet_length(engine_binary_sha256) = 32",
            name="baseline_runs_engine_sha256_length",
        ),
        sa.CheckConstraint("per_bucket_sample > 0", name="baseline_runs_per_bucket_positive"),
        sa.CheckConstraint("depth > 0", name="baseline_runs_depth_positive"),
        sa.CheckConstraint("multipv > 0", name="baseline_runs_multipv_positive"),
        sa.CheckConstraint("workers > 0", name="baseline_runs_workers_positive"),
        sa.CheckConstraint(
            "status IN ('running','completed','failed','aborted')",
            name="baseline_runs_status_check",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="baseline_runs_time_check",
        ),
    )

    op.create_table(
        "pgn_corpus",
        sa.Column("pgn_sha256", sa.LargeBinary, primary_key=True),
        sa.Column("pgn_text", sa.Text, nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.CheckConstraint(
            "octet_length(pgn_sha256) = 32",
            name="pgn_corpus_sha256_length",
        ),
    )

    op.create_table(
        "baseline_samples",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("baseline_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("bucket_label", sa.String(16), nullable=False),
        sa.Column("pgn_sha256", sa.LargeBinary, nullable=False),
        sa.Column("white_elo", sa.Integer, nullable=True),
        sa.Column("black_elo", sa.Integer, nullable=True),
        sa.Column("time_control", sa.String(32), nullable=True),
        sa.Column("ply_count", sa.Integer, nullable=True),
        sa.Column("reservoir_position", sa.Integer, nullable=False),
        sa.Column(
            "sampled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "analysed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("FALSE"),
        ),
        sa.ForeignKeyConstraint(
            ["pgn_sha256"],
            ["pgn_corpus.pgn_sha256"],
            name="baseline_samples_pgn_fk",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint(
            "run_id",
            "bucket_label",
            "reservoir_position",
            name="baseline_samples_position_unique",
        ),
        sa.CheckConstraint(
            "white_elo IS NULL OR white_elo BETWEEN 600 AND 3500",
            name="baseline_samples_white_elo_range",
        ),
        sa.CheckConstraint(
            "black_elo IS NULL OR black_elo BETWEEN 600 AND 3500",
            name="baseline_samples_black_elo_range",
        ),
        sa.CheckConstraint(
            "ply_count IS NULL OR ply_count >= 0",
            name="baseline_samples_ply_count_nonneg",
        ),
        sa.CheckConstraint(
            "reservoir_position >= 0",
            name="baseline_samples_position_nonneg",
        ),
        sa.CheckConstraint(
            "bucket_label IN ('≤1200','1201-1500','1501-1800','1801-2100','2101-2400','2401+')",
            name="baseline_samples_bucket_check",
        ),
    )

    # Partial index for the worker claim query (analysed=FALSE rows only).
    # NULLS FIRST puts never-claimed rows ahead of stale-claimed rows.
    op.create_index(
        "idx_baseline_samples_pending",
        "baseline_samples",
        ["run_id", sa.text("claimed_at NULLS FIRST")],
        postgresql_where=sa.text("analysed = FALSE"),
    )

    op.create_table(
        "baseline_analyses",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "sample_id",
            UUID(as_uuid=True),
            sa.ForeignKey("baseline_samples.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("top1_rate", sa.Float(precision=53), nullable=False),
        sa.Column("weighted_rate", sa.Float(precision=53), nullable=False),
        sa.Column("acpl", sa.Float(precision=53), nullable=False),
        sa.Column("eligible_plies", sa.Integer, nullable=False),
        sa.Column(
            "analysed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("analysis_duration_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.UniqueConstraint("sample_id", name="baseline_analyses_sample_unique"),
        sa.CheckConstraint(
            "top1_rate BETWEEN 0 AND 1",
            name="baseline_analyses_top1_rate_range",
        ),
        sa.CheckConstraint(
            "weighted_rate BETWEEN 0 AND 1",
            name="baseline_analyses_weighted_rate_range",
        ),
        sa.CheckConstraint("acpl >= 0", name="baseline_analyses_acpl_nonneg"),
        sa.CheckConstraint(
            "eligible_plies >= 0",
            name="baseline_analyses_eligible_plies_nonneg",
        ),
        sa.CheckConstraint(
            "analysis_duration_ms IS NULL OR analysis_duration_ms >= 0",
            name="baseline_analyses_duration_nonneg",
        ),
    )

    # Function MUST be created before trigger.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION fn_mark_sample_analysed()
        RETURNS TRIGGER AS $$
        BEGIN
          UPDATE baseline_samples
          SET analysed = TRUE
          WHERE id = NEW.sample_id;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_mark_sample_analysed
        AFTER INSERT ON baseline_analyses
        FOR EACH ROW
        EXECUTE FUNCTION fn_mark_sample_analysed();
        """
    )

    # Returns 6 rated buckets. The 7th (rating-unknown) is computed in
    # Python from the elementwise median of these 6 rows.
    op.execute(
        """
        CREATE VIEW baseline_buckets AS
        SELECT
          s.run_id,
          s.bucket_label,
          COUNT(a.id)                             AS sample_size,
          AVG(a.top1_rate)::DOUBLE PRECISION      AS expected_top1,
          AVG(a.weighted_rate)::DOUBLE PRECISION  AS expected_weighted_top1,
          AVG(a.acpl)::DOUBLE PRECISION           AS expected_acpl_mean,
          STDDEV_POP(a.acpl)::DOUBLE PRECISION    AS expected_acpl_stdev
        FROM baseline_samples s
        JOIN baseline_analyses a ON a.sample_id = s.id
        WHERE a.eligible_plies >= 10 AND a.error_message IS NULL
        GROUP BY s.run_id, s.bucket_label;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS baseline_buckets")
    op.execute("DROP TRIGGER IF EXISTS trg_mark_sample_analysed ON baseline_analyses")
    op.execute("DROP FUNCTION IF EXISTS fn_mark_sample_analysed()")
    op.drop_table("baseline_analyses")
    op.drop_index("idx_baseline_samples_pending", table_name="baseline_samples")
    op.drop_table("baseline_samples")
    op.drop_table("pgn_corpus")
    op.drop_table("baseline_runs")
    # pgcrypto stays installed (used by audit_runs + future tables).
