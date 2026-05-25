"""SQLAlchemy declarative models for the analysis cache.

Feature 008. Matches the schema in `migrations/versions/0001_init.py`
exactly — the two are kept in lockstep manually (no autogenerate magic
for the initial revision; later migrations may use it).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Float,
    Index,
    Integer,
    LargeBinary,
    String,
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
