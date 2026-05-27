"""chess.com banned-account crawl state (feature 013).

Revision ID: 0004_chesscom_crawl
Revises: 0003_audit_jobs
Create Date: 2026-05-26
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0004_chesscom_crawl"
down_revision: str | Sequence[str] | None = "0003_audit_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chesscom_crawl_status",
        sa.Column("username", sa.String(64), primary_key=True),
        sa.Column("status", sa.String(64), nullable=False),
        sa.Column("depth_from_seed", sa.Integer, nullable=False),
        sa.Column("seed_username", sa.String(64), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("games_pulled", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("profile_json", JSONB, nullable=True),
        sa.CheckConstraint(
            "depth_from_seed >= 0",
            name="chesscom_crawl_status_depth_nonneg",
        ),
        sa.CheckConstraint(
            "games_pulled >= 0",
            name="chesscom_crawl_status_games_nonneg",
        ),
    )

    # Partial index on confirmed fair-play bans for the "candidates to pull
    # PGNs from" query the crawler runs once per visited username.
    op.create_index(
        "idx_chesscom_crawl_banned",
        "chesscom_crawl_status",
        ["depth_from_seed"],
        postgresql_where=sa.text("status LIKE 'closed:fair_play%'"),
    )

    # Convenience index for resume — by seed + depth lookups during BFS.
    op.create_index(
        "idx_chesscom_crawl_seed_depth",
        "chesscom_crawl_status",
        ["seed_username", "depth_from_seed"],
    )


def downgrade() -> None:
    op.drop_index("idx_chesscom_crawl_seed_depth", table_name="chesscom_crawl_status")
    op.drop_index("idx_chesscom_crawl_banned", table_name="chesscom_crawl_status")
    op.drop_table("chesscom_crawl_status")
