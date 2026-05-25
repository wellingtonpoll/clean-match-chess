"""Initial schema — audit_runs table (feature 008).

Revision ID: 0001_init
Revises:
Create Date: 2026-05-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0001_init"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "audit_runs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("pgn_sha256", sa.LargeBinary, nullable=False),
        sa.Column("manifest_sha256", sa.LargeBinary, nullable=False),
        sa.Column("platform", sa.String(16), nullable=True),
        sa.Column("game_id", sa.String(64), nullable=True),
        sa.Column("white_username", sa.String(64), nullable=True),
        sa.Column("black_username", sa.String(64), nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("risk_level", sa.String(8), nullable=True),
        sa.Column("ply_count", sa.Integer, nullable=True),
        sa.Column("run_json", JSONB, nullable=False),
        sa.Column("manifest_json", JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        # Reserved for feature 009+ (auth + multi-tenancy). No FK constraints.
        sa.Column("user_id", UUID(as_uuid=True), nullable=True),
        sa.Column("tenant_id", UUID(as_uuid=True), nullable=True),
        sa.UniqueConstraint(
            "pgn_sha256", "manifest_sha256", name="audit_runs_pgn_manifest_unique"
        ),
    )

    op.create_index(
        "idx_audit_runs_platform_game",
        "audit_runs",
        ["platform", "game_id"],
    )
    op.create_index("idx_audit_runs_white", "audit_runs", ["white_username"])
    op.create_index("idx_audit_runs_black", "audit_runs", ["black_username"])
    op.create_index(
        "idx_audit_runs_created",
        "audit_runs",
        [sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("idx_audit_runs_created", table_name="audit_runs")
    op.drop_index("idx_audit_runs_black", table_name="audit_runs")
    op.drop_index("idx_audit_runs_white", table_name="audit_runs")
    op.drop_index("idx_audit_runs_platform_game", table_name="audit_runs")
    op.drop_table("audit_runs")
    # Leave pgcrypto in place — it's a database-level extension that other
    # tables (added in feature 009+) will continue to need.
