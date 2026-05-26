"""Tests for `analysis_core.db.audit_jobs` (feature 011 Phase 3).

Requires a running Postgres at `DATABASE_URL`. Skips cleanly when unset
or unreachable. Mirrors the pattern from `test_baseline_store.py`.
"""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from analysis_core.db.audit_jobs import (
    claim_next_job,
    enqueue,
    get_status,
    mark_completed,
    mark_failed,
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
        pytest.skip("DATABASE_URL not set — audit_jobs suite skipped")
    if not _db_available(url):
        pytest.skip(f"Postgres at {url!r} unreachable — audit_jobs suite skipped")
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
def clean_audit_jobs(migrated_db: str) -> Iterator[None]:
    engine = create_engine(migrated_db)
    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE audit_jobs"))
        yield
    finally:
        engine.dispose()


_MINI_PGN = (
    '[Event "Test"]\n[White "a"]\n[Black "b"]\n[Result "*"]\n[TimeControl "600+0"]\n\n1. e4 e5 *\n'
)


class TestEnqueue:
    def test_inserts_queued_row(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN, subject_color="white")
            session.commit()
            assert isinstance(job_id, uuid.UUID)

            row = session.execute(
                text(
                    "SELECT status, subject_color, octet_length(pgn_sha256) "
                    "FROM audit_jobs WHERE id = :id"
                ),
                {"id": job_id},
            ).first()
            assert row.status == "queued"
            assert row.subject_color == "white"
            assert row.octet_length == 32  # sha256 is 32 bytes

    def test_rejects_invalid_color(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            with pytest.raises(ValueError, match="subject_color"):
                enqueue(session, pgn_text=_MINI_PGN, subject_color="green")


class TestClaimNextJob:
    def test_claims_oldest_queued(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            first = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()

        with session_factory() as session:
            claimed = claim_next_job(session)
            assert claimed is not None
            assert claimed.job_id == first
            session.commit()
            # Status should now be 'running'.
            status = session.execute(
                text("SELECT status FROM audit_jobs WHERE id = :id"), {"id": first}
            ).scalar_one()
            assert status == "running"

    def test_returns_none_when_empty(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            assert claim_next_job(session) is None

    def test_skip_locked_no_double_claim(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            a = enqueue(session, pgn_text=_MINI_PGN + "; a\n")
            b = enqueue(session, pgn_text=_MINI_PGN + "; b\n")
            session.commit()

        s1 = session_factory()
        s2 = session_factory()
        try:
            c1 = claim_next_job(s1)
            c2 = claim_next_job(s2)
            assert c1 is not None and c2 is not None
            assert c1.job_id != c2.job_id
            assert {c1.job_id, c2.job_id} == {a, b}
            s1.commit()
            s2.commit()
        finally:
            s1.close()
            s2.close()

    def test_stale_running_reclaim(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()

        # Worker A claims, then "crashes" without persisting result.
        with session_factory() as session:
            claim_next_job(session)
            session.commit()

        # Backdate claimed_at to 30 min ago.
        with session_factory() as session:
            session.execute(
                text(
                    "UPDATE audit_jobs SET claimed_at = NOW() - INTERVAL '30 minutes' "
                    "WHERE id = :id"
                ),
                {"id": job_id},
            )
            session.commit()

        # New worker should re-claim.
        with session_factory() as session:
            reclaim = claim_next_job(session)
            assert reclaim is not None
            assert reclaim.job_id == job_id


class TestMarkCompleted:
    def test_persists_result_json(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()

        with session_factory() as session:
            claimed = claim_next_job(session)
            session.commit()
            mark_completed(
                session,
                job_id=claimed.job_id,
                result_json={"score": 0.42, "risk_level": "medium"},
                audit_run_id=uuid.uuid4(),
            )
            session.commit()

        with session_factory() as session:
            status = get_status(session, job_id=job_id)
            assert status is not None
            assert status.status == "completed"
            assert status.result_json == {"score": 0.42, "risk_level": "medium"}
            assert status.audit_run_id is not None


class TestMarkFailed:
    def test_persists_error_message(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()

        with session_factory() as session:
            mark_failed(session, job_id=job_id, error_message="boom: stockfish crashed")
            session.commit()

        with session_factory() as session:
            status = get_status(session, job_id=job_id)
            assert status is not None
            assert status.status == "failed"
            assert status.error_message == "boom: stockfish crashed"

    def test_truncates_long_message(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()

        with session_factory() as session:
            mark_failed(session, job_id=job_id, error_message="x" * 10000)
            session.commit()

        with session_factory() as session:
            status = get_status(session, job_id=job_id)
            assert status is not None
            assert status.error_message is not None
            assert len(status.error_message) == 4000

    def test_rejects_invalid_status(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            job_id = enqueue(session, pgn_text=_MINI_PGN)
            session.commit()
            with pytest.raises(ValueError, match="invalid terminal status"):
                mark_failed(session, job_id=job_id, error_message="x", status="nope")


class TestGetStatus:
    def test_unknown_returns_none(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            assert get_status(session, job_id=uuid.uuid4()) is None
