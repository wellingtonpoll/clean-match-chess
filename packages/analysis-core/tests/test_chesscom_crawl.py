"""Tests for `analysis_core.db.chesscom_crawl` (feature 013)."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from analysis_core.db.chesscom_crawl import (
    crawl_summary,
    increment_games_pulled,
    is_already_visited,
    list_banned,
    record_visit,
)
from analysis_core.db.session import init_engine
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[3]
ALEMBIC_INI = REPO_ROOT / "packages" / "analysis-core" / "alembic.ini"


def _db_available(url: str) -> bool:
    try:
        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


@pytest.fixture(scope="module")
def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — chesscom_crawl suite skipped")
    if not _db_available(url):
        pytest.skip(f"Postgres at {url!r} unreachable — chesscom_crawl suite skipped")
    return url


@pytest.fixture(scope="module")
def migrated_db(database_url: str) -> str:
    env = {**os.environ, "DATABASE_URL": database_url}
    result = subprocess.run(  # noqa: S603 — trusted argv
        ["uv", "run", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],  # noqa: S607 — system uv binary
        env=env,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"alembic upgrade failed:\n{result.stderr}"
    return database_url


@pytest.fixture
def session_factory(migrated_db: str) -> Iterator[sessionmaker[Session]]:
    init_engine(migrated_db)
    from analysis_core.db import session as session_module
    from analysis_core.db.session import get_session_factory

    factory = get_session_factory()
    assert factory is not None
    yield factory
    if session_module._engine is not None:
        session_module._engine.dispose()
        session_module._engine = None
        session_module._session_factory = None
        session_module._init_attempted = False
        session_module._init_failure_reason = None


@pytest.fixture(autouse=True)
def clean_crawl_table(migrated_db: str) -> Iterator[None]:
    engine = create_engine(migrated_db)
    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE chesscom_crawl_status"))
        yield
    finally:
        engine.dispose()


class TestRecordVisit:
    def test_inserts_new_row(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session,
                username="quaiada",
                status="closed:fair_play_violations",
                depth_from_seed=0,
                seed_username="quaiada",
                profile_json={"player_id": 89132312},
            )
            session.commit()
            row = session.execute(
                text(
                    "SELECT username, status, depth_from_seed, seed_username, profile_json "
                    "FROM chesscom_crawl_status WHERE username = :u"
                ),
                {"u": "quaiada"},
            ).one()
            assert row.username == "quaiada"
            assert row.status == "closed:fair_play_violations"
            assert row.depth_from_seed == 0
            assert row.seed_username == "quaiada"
            assert row.profile_json["player_id"] == 89132312

    def test_idempotent_upsert(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session, username="bob", status="basic", depth_from_seed=2, seed_username="quaiada"
            )
            # Re-visit with same depth — should keep row, update status.
            record_visit(
                session,
                username="bob",
                status="closed:abuse",
                depth_from_seed=2,
                seed_username="quaiada",
            )
            session.commit()
            status = session.execute(
                text("SELECT status FROM chesscom_crawl_status WHERE username = :u"),
                {"u": "bob"},
            ).scalar_one()
            assert status == "closed:abuse"

    def test_depth_takes_smaller_on_conflict(self, session_factory: sessionmaker[Session]) -> None:
        """Re-visiting via a shorter path should LOWER depth, not raise it."""
        with session_factory() as session:
            record_visit(
                session,
                username="charlie",
                status="basic",
                depth_from_seed=2,
                seed_username="quaiada",
            )
            # Visit again via a closer path.
            record_visit(
                session,
                username="charlie",
                status="basic",
                depth_from_seed=1,
                seed_username="quaiada",
            )
            session.commit()
            depth = session.execute(
                text("SELECT depth_from_seed FROM chesscom_crawl_status WHERE username = :u"),
                {"u": "charlie"},
            ).scalar_one()
            assert depth == 1

    def test_depth_does_not_increase_on_conflict(
        self, session_factory: sessionmaker[Session]
    ) -> None:
        """If a later visit reports a LARGER depth, keep the smaller one."""
        with session_factory() as session:
            record_visit(
                session,
                username="diana",
                status="basic",
                depth_from_seed=1,
                seed_username="quaiada",
            )
            record_visit(
                session,
                username="diana",
                status="basic",
                depth_from_seed=3,
                seed_username="quaiada",
            )
            session.commit()
            depth = session.execute(
                text("SELECT depth_from_seed FROM chesscom_crawl_status WHERE username = :u"),
                {"u": "diana"},
            ).scalar_one()
            assert depth == 1


class TestIsAlreadyVisited:
    def test_returns_false_for_unknown(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            assert is_already_visited(session, username="nobody") is False

    def test_returns_true_after_visit(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session, username="seen", status="basic", depth_from_seed=0, seed_username="seen"
            )
            session.commit()
            assert is_already_visited(session, username="seen") is True


class TestIncrementGamesPulled:
    def test_adds_to_counter(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session,
                username="cheater",
                status="closed:fair_play_violations",
                depth_from_seed=1,
                seed_username="seed",
            )
            session.commit()
            increment_games_pulled(session, username="cheater", by=3)
            increment_games_pulled(session, username="cheater", by=2)
            session.commit()
            count = session.execute(
                text("SELECT games_pulled FROM chesscom_crawl_status WHERE username = :u"),
                {"u": "cheater"},
            ).scalar_one()
            assert count == 5


class TestListBanned:
    def test_returns_only_fair_play_banned(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session,
                username="cheater1",
                status="closed:fair_play_violations",
                depth_from_seed=1,
                seed_username="seed",
            )
            record_visit(
                session, username="clean1", status="basic", depth_from_seed=1, seed_username="seed"
            )
            record_visit(
                session,
                username="abuse1",
                status="closed:abuse",
                depth_from_seed=1,
                seed_username="seed",
            )
            session.commit()
            banned = list_banned(session)
            usernames = {b.username for b in banned}
            assert usernames == {"cheater1"}

    def test_max_depth_filter(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session,
                username="deep_cheater",
                status="closed:fair_play_violations",
                depth_from_seed=3,
                seed_username="seed",
            )
            record_visit(
                session,
                username="shallow_cheater",
                status="closed:fair_play_violations",
                depth_from_seed=1,
                seed_username="seed",
            )
            session.commit()
            shallow = list_banned(session, max_depth=2)
            assert {b.username for b in shallow} == {"shallow_cheater"}

    def test_limit(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            for i in range(5):
                record_visit(
                    session,
                    username=f"c{i}",
                    status="closed:fair_play_violations",
                    depth_from_seed=1,
                    seed_username="seed",
                )
            session.commit()
            limited = list_banned(session, limit=3)
            assert len(limited) == 3


class TestCrawlSummary:
    def test_aggregates(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            record_visit(
                session,
                username="c1",
                status="closed:fair_play_violations",
                depth_from_seed=0,
                seed_username="c1",
            )
            record_visit(
                session, username="u1", status="basic", depth_from_seed=1, seed_username="c1"
            )
            session.commit()
            increment_games_pulled(session, username="c1", by=7)
            session.commit()

            summary = crawl_summary(session)
            assert summary["banned"] == 1
            assert summary["not_banned"] == 1
            assert summary["total"] == 2
            assert summary["games_pulled"] == 7
