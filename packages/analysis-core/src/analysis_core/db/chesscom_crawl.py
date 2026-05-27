"""Repository layer for the chess.com banned-account crawler (feature 013).

Backs `scripts/build_engine_assisted_corpus.py`. Persists BFS state so a
multi-hour crawl can resume after interrupt. The crawler is rate-limited
by chess.com pub API (~30 req/min unauthenticated); persisting per
visited username avoids repeating expensive profile checks.

All functions raise on DB errors — this is a maintainer operation, not
a graceful-degrade path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from analysis_core.db.models import ChesscomCrawlStatusModel

_FAIR_PLAY_PREFIX = "closed:fair_play"


@dataclass(frozen=True)
class CrawlRecord:
    """One row from `chesscom_crawl_status` exposed to the crawler driver."""

    username: str
    status: str
    depth_from_seed: int
    seed_username: str
    games_pulled: int


def record_visit(
    session: Session,
    *,
    username: str,
    status: str,
    depth_from_seed: int,
    seed_username: str,
    profile_json: dict[str, Any] | None = None,
) -> None:
    """Upsert one row. Idempotent — re-visiting same username updates `status`
    + `checked_at` but preserves `depth_from_seed` and `seed_username` from
    the first visit (don't downgrade depth when a later seed finds the
    same user closer)."""
    stmt = pg_insert(ChesscomCrawlStatusModel).values(
        username=username,
        status=status,
        depth_from_seed=depth_from_seed,
        seed_username=seed_username,
        profile_json=profile_json,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["username"],
        set_={
            "status": stmt.excluded.status,
            "checked_at": text("NOW()"),
            "profile_json": stmt.excluded.profile_json,
            # depth_from_seed: keep the SMALLER (closer-to-seed) depth.
            "depth_from_seed": text(
                "LEAST(chesscom_crawl_status.depth_from_seed, EXCLUDED.depth_from_seed)"
            ),
        },
    )
    session.execute(stmt)


def increment_games_pulled(session: Session, *, username: str, by: int = 1) -> None:
    session.execute(
        text(
            "UPDATE chesscom_crawl_status "
            "SET games_pulled = games_pulled + :by "
            "WHERE username = :username"
        ),
        {"username": username, "by": by},
    )


def is_already_visited(session: Session, *, username: str) -> bool:
    """True iff the crawler has already checked this user's profile."""
    return (
        session.execute(
            select(ChesscomCrawlStatusModel.username).where(
                ChesscomCrawlStatusModel.username == username
            )
        ).first()
        is not None
    )


def list_banned(
    session: Session,
    *,
    max_depth: int | None = None,
    limit: int | None = None,
) -> list[CrawlRecord]:
    """Return all users with `status LIKE 'closed:fair_play%'`, oldest-visited first.

    `max_depth`: cap on `depth_from_seed`. None = no cap.
    `limit`: cap on rows. None = no cap.
    """
    stmt = (
        select(ChesscomCrawlStatusModel)
        .where(ChesscomCrawlStatusModel.status.like(f"{_FAIR_PLAY_PREFIX}%"))
        .order_by(ChesscomCrawlStatusModel.checked_at)
    )
    if max_depth is not None:
        stmt = stmt.where(ChesscomCrawlStatusModel.depth_from_seed <= max_depth)
    if limit is not None:
        stmt = stmt.limit(limit)
    rows = session.execute(stmt).scalars().all()
    return [
        CrawlRecord(
            username=r.username,
            status=r.status,
            depth_from_seed=r.depth_from_seed,
            seed_username=r.seed_username,
            games_pulled=r.games_pulled,
        )
        for r in rows
    ]


def crawl_summary(session: Session) -> dict[str, int]:
    """Aggregate counts for crawler status reporting."""
    return dict(
        session.execute(
            text(
                """
                SELECT
                  COUNT(*) FILTER (WHERE status LIKE 'closed:fair_play%')   AS banned,
                  COUNT(*) FILTER (WHERE status NOT LIKE 'closed:fair_play%') AS not_banned,
                  COUNT(*)                                                  AS total,
                  COALESCE(SUM(games_pulled), 0)                            AS games_pulled
                FROM chesscom_crawl_status
                """
            )
        )
        .one()
        ._mapping
    )
