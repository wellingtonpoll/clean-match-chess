"""Tests for `analysis_core.db.baseline_store` (feature 007).

Requires a running Postgres at `DATABASE_URL`. Skips cleanly when unset
or unreachable. Mirrors the pattern in `tests/integration/test_postgres_cache.py`.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from analysis_core.db.baseline_store import (
    BucketAggregate,
    ReservoirSlot,
    claim_sample,
    compute_rating_unknown_row,
    create_run,
    fetch_bucket_aggregates,
    flush_reservoir,
    mark_phase1_done,
    mark_run_completed,
    mark_run_failed,
    persist_analysis,
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
        pytest.skip("DATABASE_URL not set — baseline_store suite skipped")
    if not _db_available(url):
        pytest.skip(f"Postgres at {url!r} unreachable — baseline_store suite skipped")
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
    # Dispose pooled connections so the process-global engine doesn't leak
    # them — `filterwarnings = ["error"]` in pyproject.toml otherwise turns
    # the unraisable psycopg GC warning into a teardown ERROR.
    if session_module._engine is not None:
        session_module._engine.dispose()
        session_module._engine = None
        session_module._session_factory = None
        session_module._init_attempted = False
        session_module._init_failure_reason = None


@pytest.fixture(autouse=True)
def clean_baseline_tables(migrated_db: str) -> Iterator[None]:
    """Truncate baseline tables before each test.

    Avoids stomping on a long-running real build by skipping when the
    notes field marks a non-test run. Tests with `_mk_run()` write
    notes=None so the truncate always proceeds; real builds via
    `build_baselines.py` write notes='T007 v2 ...' or similar.
    """
    engine = create_engine(migrated_db)
    try:
        with engine.connect() as conn:
            external = conn.execute(
                text(
                    "SELECT COUNT(*) FROM baseline_runs "
                    "WHERE status = 'running' AND notes IS NOT NULL "
                    "AND started_at > NOW() - INTERVAL '10 minutes'"
                )
            ).scalar_one()
            if external > 0:
                pytest.skip(
                    f"{external} fresh baseline_runs.status='running' with notes "
                    "(likely a real build) — refusing to truncate."
                )
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE TABLE baseline_runs CASCADE"))
            conn.execute(text("TRUNCATE TABLE pgn_corpus CASCADE"))
        yield
    finally:
        engine.dispose()


def _sha32(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _mk_slot(bucket: str, pos: int, pgn_seed: str, *, elo: int = 1500) -> ReservoirSlot:
    pgn_text = f'[Event "test {pgn_seed}"]\n\n1. e4 e5 *\n'
    return ReservoirSlot(
        bucket_label=bucket,
        reservoir_position=pos,
        pgn_sha256=_sha32(pgn_text.encode()),
        pgn_text=pgn_text,
        white_elo=elo,
        black_elo=elo,
        time_control="600+0",
        ply_count=2,
    )


def _mk_run(session: Session) -> uuid.UUID:
    return create_run(
        session,
        archive_sha256=_sha32(b"archive"),
        source_dataset="lichess-2026-04",
        seed=0,
        per_bucket_sample=5,
        depth=10,
        multipv=3,
        workers=6,
        engine_binary_sha256=_sha32(b"engine"),
        script_version="0.2.0",
    )


class TestCreateRun:
    def test_inserts_running_row(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            session.commit()
            assert isinstance(run_id, uuid.UUID)
            row = session.execute(
                text("SELECT status, total_analysed FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).first()
            assert row.status == "running"
            assert row.total_analysed == 0


class TestFlushReservoir:
    def test_insert_then_upsert(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            slots1 = [_mk_slot("1501-1800", 0, "a"), _mk_slot("1501-1800", 1, "b")]
            flush_reservoir(session, run_id=run_id, slots=slots1, total_scanned=100_000)
            session.commit()

            count = session.execute(
                text("SELECT COUNT(*) FROM baseline_samples WHERE run_id = :id"),
                {"id": run_id},
            ).scalar_one()
            assert count == 2

            # Overwrite position 0 with new PGN (Algorithm L replacement)
            slots2 = [_mk_slot("1501-1800", 0, "c", elo=1600)]
            flush_reservoir(session, run_id=run_id, slots=slots2, total_scanned=200_000)
            session.commit()

            still_two = session.execute(
                text("SELECT COUNT(*) FROM baseline_samples WHERE run_id = :id"),
                {"id": run_id},
            ).scalar_one()
            assert still_two == 2

            pos0 = session.execute(
                text(
                    "SELECT white_elo FROM baseline_samples "
                    "WHERE run_id = :id AND reservoir_position = 0"
                ),
                {"id": run_id},
            ).scalar_one()
            assert pos0 == 1600

    def test_empty_slots_still_updates_scanned(
        self, session_factory: sessionmaker[Session]
    ) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(session, run_id=run_id, slots=[], total_scanned=500_000)
            session.commit()
            scanned = session.execute(
                text("SELECT total_scanned FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).scalar_one()
            assert scanned == 500_000


class TestClaimSample:
    def test_claims_pending_sample(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(session, run_id=run_id, slots=[_mk_slot("≤1200", 0, "x")])
            session.commit()

        with session_factory() as session:
            claimed = claim_sample(session, run_id=run_id)
            assert claimed is not None
            assert claimed.bucket_label == "≤1200"
            assert "1. e4" in claimed.pgn_text
            session.commit()

    def test_returns_none_when_all_analysed(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            session.commit()

        with session_factory() as session:
            assert claim_sample(session, run_id=run_id) is None

    def test_skip_locked_no_double_claim(self, session_factory: sessionmaker[Session]) -> None:
        """Two concurrent transactions claim DIFFERENT samples."""
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(
                session,
                run_id=run_id,
                slots=[_mk_slot("≤1200", 0, "p"), _mk_slot("≤1200", 1, "q")],
            )
            session.commit()

        s1 = session_factory()
        s2 = session_factory()
        try:
            c1 = claim_sample(s1, run_id=run_id)
            c2 = claim_sample(s2, run_id=run_id)
            assert c1 is not None and c2 is not None
            assert c1.sample_id != c2.sample_id
            s1.commit()
            s2.commit()
        finally:
            s1.close()
            s2.close()

    def test_stale_claim_recoverable(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(session, run_id=run_id, slots=[_mk_slot("≤1200", 0, "old")])
            session.commit()

        # Worker A claims, then "crashes" (commits claim, never inserts analysis)
        with session_factory() as session:
            claimed = claim_sample(session, run_id=run_id)
            assert claimed is not None
            sample_id = claimed.sample_id
            session.commit()

        # Set claimed_at 30 minutes ago to simulate staleness
        with session_factory() as session:
            session.execute(
                text(
                    "UPDATE baseline_samples "
                    "SET claimed_at = NOW() - INTERVAL '30 minutes' WHERE id = :id"
                ),
                {"id": sample_id},
            )
            session.commit()

        # Fresh worker re-claims the stale sample
        with session_factory() as session:
            reclaim = claim_sample(session, run_id=run_id)
            assert reclaim is not None
            assert reclaim.sample_id == sample_id
            session.commit()


class TestPersistAnalysis:
    def test_trigger_marks_sample_analysed(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(session, run_id=run_id, slots=[_mk_slot("1801-2100", 0, "y")])
            session.commit()

        with session_factory() as session:
            claimed = claim_sample(session, run_id=run_id)
            assert claimed is not None
            session.commit()

        with session_factory() as session:
            persist_analysis(
                session,
                sample_id=claimed.sample_id,
                top1_rate=0.55,
                weighted_rate=0.72,
                acpl=35.0,
                eligible_plies=60,
                analysis_duration_ms=2500,
            )
            session.commit()

        with session_factory() as session:
            analysed, count = session.execute(
                text(
                    """
                    SELECT s.analysed, br.total_analysed
                    FROM baseline_samples s
                    JOIN baseline_runs br ON br.id = s.run_id
                    WHERE s.id = :id
                    """
                ),
                {"id": claimed.sample_id},
            ).first()
            assert analysed is True
            assert count == 1

    def test_error_message_persisted(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            flush_reservoir(session, run_id=run_id, slots=[_mk_slot("2401+", 0, "z")])
            session.commit()

        with session_factory() as session:
            claimed = claim_sample(session, run_id=run_id)
            persist_analysis(
                session,
                sample_id=claimed.sample_id,
                top1_rate=0.0,
                weighted_rate=0.0,
                acpl=0.0,
                eligible_plies=0,
                error_message="stockfish timeout",
            )
            session.commit()

        with session_factory() as session:
            err = session.execute(
                text("SELECT error_message FROM baseline_analyses WHERE sample_id = :id"),
                {"id": claimed.sample_id},
            ).scalar_one()
            assert err == "stockfish timeout"


class TestAggregates:
    def test_view_excludes_low_ply_and_errors(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            slots = [_mk_slot("1201-1500", i, f"g{i}") for i in range(3)]
            flush_reservoir(session, run_id=run_id, slots=slots)
            session.commit()

        # 3 analyses: one OK, one low-ply, one errored
        claims: list[uuid.UUID] = []
        for _ in range(3):
            with session_factory() as session:
                c = claim_sample(session, run_id=run_id)
                claims.append(c.sample_id)
                session.commit()

        with session_factory() as session:
            persist_analysis(
                session,
                sample_id=claims[0],
                top1_rate=0.6,
                weighted_rate=0.75,
                acpl=25.0,
                eligible_plies=40,
            )
            persist_analysis(
                session,
                sample_id=claims[1],
                top1_rate=0.5,
                weighted_rate=0.6,
                acpl=80.0,
                eligible_plies=5,  # < 10 → excluded from view
            )
            persist_analysis(
                session,
                sample_id=claims[2],
                top1_rate=0.0,
                weighted_rate=0.0,
                acpl=0.0,
                eligible_plies=0,
                error_message="boom",
            )
            session.commit()

        with session_factory() as session:
            aggs = fetch_bucket_aggregates(session, run_id=run_id)
            assert len(aggs) == 1
            assert aggs[0].bucket_label == "1201-1500"
            assert aggs[0].sample_size == 1
            assert aggs[0].expected_top1 == pytest.approx(0.6)
            assert aggs[0].expected_acpl_mean == pytest.approx(25.0)


class TestRatingUnknown:
    def test_elementwise_median(self) -> None:
        rated = [
            BucketAggregate("≤1200", 100, 0.30, 0.45, 70.0, 30.0),
            BucketAggregate("1201-1500", 100, 0.35, 0.50, 60.0, 28.0),
            BucketAggregate("1501-1800", 110, 0.45, 0.60, 45.0, 22.0),
            BucketAggregate("1801-2100", 120, 0.55, 0.70, 35.0, 18.0),
            BucketAggregate("2101-2400", 130, 0.65, 0.80, 25.0, 14.0),
            BucketAggregate("2401+", 140, 0.75, 0.88, 18.0, 10.0),
        ]
        unknown = compute_rating_unknown_row(rated)
        assert unknown.bucket_label == "rating-unknown"
        # Median of 6 values = average of 3rd and 4th
        assert unknown.expected_top1 == pytest.approx((0.45 + 0.55) / 2)
        assert unknown.expected_acpl_mean == pytest.approx((45.0 + 35.0) / 2)
        # sample_size is the min (most conservative)
        assert unknown.sample_size == 100

    def test_empty_raises(self) -> None:
        with pytest.raises(ValueError):
            compute_rating_unknown_row([])


class TestRunLifecycle:
    def test_mark_completed(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            mark_phase1_done(session, run_id=run_id, total_sampled=12345)
            mark_run_completed(session, run_id=run_id)
            session.commit()

            row = session.execute(
                text("SELECT status, total_sampled, finished_at FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).first()
            assert row.status == "completed"
            assert row.total_sampled == 12345
            assert row.finished_at is not None

    def test_mark_failed(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            mark_run_failed(session, run_id=run_id, error_message="oom in worker 3")
            session.commit()

            row = session.execute(
                text("SELECT status, error_message FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).first()
            assert row.status == "failed"
            assert row.error_message == "oom in worker 3"

    def test_mark_aborted(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            mark_run_failed(session, run_id=run_id, error_message="SIGINT", status="aborted")
            session.commit()

            status = session.execute(
                text("SELECT status FROM baseline_runs WHERE id = :id"),
                {"id": run_id},
            ).scalar_one()
            assert status == "aborted"

    def test_invalid_status_rejected(self, session_factory: sessionmaker[Session]) -> None:
        with session_factory() as session:
            run_id = _mk_run(session)
            with pytest.raises(ValueError):
                mark_run_failed(session, run_id=run_id, error_message="x", status="nope")
