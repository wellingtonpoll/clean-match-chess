#!/usr/bin/env python3
"""Long-running audit worker daemon (feature 011 Phase 3).

Listens on Postgres NOTIFY channel `audit_jobs_new`, claims each job via
`SELECT FOR UPDATE SKIP LOCKED`, runs the audit pipeline via the engine
pool, and persists the result. The frontend's API routes never invoke
Stockfish directly — they POST to enqueue + GET to poll status.

Single-process; multiple instances on the same database safely drain in
parallel thanks to `SKIP LOCKED`. Restart-safe: stale-running jobs are
re-claimed automatically after the 15-minute timeout in
`claim_next_job`.

Environment:
  DATABASE_URL              — required.
  CLEANMATCH_ENGINE_IMAGE   — Stockfish container image (preferred for prod).
  CLEANMATCH_ENGINE_PATH    — local Stockfish binary (alternative).
  CLEANMATCH_POOL_SIZE      — default cpu_count - 2.
  CLEANMATCH_ENGINE_DEPTH   — default 12.
  CLEANMATCH_ENGINE_MULTIPV — default 3.

Run:
  uv run python apps/frontend/lib/audit_worker.py
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import time
import traceback
import uuid

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

import psycopg
from analysis_core.db.audit_jobs import claim_next_job, mark_completed, mark_failed
from analysis_core.db.session import get_session_factory, init_engine
from analysis_core.engine.stockfish_pool import EnginePool
from analysis_core.ingest.pgn_loader import is_eligible_for_scoring, load_pgn_text
from analysis_core.pipeline.run import run_single_game
from shared_types.game import PlayerColor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("audit_worker")

_LISTEN_CHANNEL = "audit_jobs_new"
_POLL_INTERVAL_S = 5.0  # fallback poll cadence when NOTIFY is quiet
_HEARTBEAT_S = 30.0


def _resolve_engine_command() -> list[str] | str:
    engine_image = os.environ.get("CLEANMATCH_ENGINE_IMAGE")
    if engine_image:
        return ["podman", "run", "--rm", "-i", engine_image]
    engine_path = os.environ.get("CLEANMATCH_ENGINE_PATH")
    if engine_path:
        return engine_path
    raise SystemExit("audit_worker requires CLEANMATCH_ENGINE_IMAGE or CLEANMATCH_ENGINE_PATH")


def _pool_size() -> int:
    raw = os.environ.get("CLEANMATCH_POOL_SIZE")
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            log.warning("invalid CLEANMATCH_POOL_SIZE=%r; falling back to default", raw)
    cpu = os.cpu_count() or 4
    return max(2, cpu - 2)


def _engine_depth() -> int:
    return int(os.environ.get("CLEANMATCH_ENGINE_DEPTH", "12"))


def _engine_multipv() -> int:
    return int(os.environ.get("CLEANMATCH_ENGINE_MULTIPV", "3"))


def _process_one_job(pool: EnginePool, session_factory) -> bool:  # type: ignore[no-untyped-def]
    """Pull + process one job. Returns True if a job was found, False otherwise."""
    with session_factory() as session:
        with session.begin():
            claimed = claim_next_job(session)
        if claimed is None:
            return False

    log.info("job.claimed id=%s sha256=%s", claimed.job_id, claimed.pgn_sha256.hex()[:16])
    t0 = time.perf_counter()
    try:
        game = load_pgn_text(claimed.pgn_text, source="async-audit")
        if not is_eligible_for_scoring(game):
            raise ValueError(f"game too short: {game.ply_count} plies")
        subject_color = PlayerColor(claimed.subject_color)

        run = run_single_game(
            game,
            subject=subject_color,
            engine_pool=pool,
            engine_depth=_engine_depth(),
            engine_multipv=_engine_multipv(),
            no_cache=False,
        )
        result_json = {
            "run_id": run.id,
            "score": run.score.score if run.score else 0.0,
            "risk_level": run.score.risk_level.value if run.score else "low",
            "confidence_interval": list(run.score.confidence_interval) if run.score else [0.0, 1.0],
            "dominant_signals": list(run.score.dominant_signals) if run.score else [],
            "ply_count": game.ply_count,
            "headers": game.headers,
            "subject": {
                "color": run.subject.color.value,
                "username": run.subject.username or "",
                "rating": run.subject.rating,
            },
        }
        with session_factory() as session:
            with session.begin():
                mark_completed(
                    session,
                    job_id=claimed.job_id,
                    result_json=result_json,
                    audit_run_id=uuid.UUID(run.id) if _is_uuid(run.id) else None,
                )
        log.info(
            "job.completed id=%s duration_ms=%d score=%.4f",
            claimed.job_id,
            int((time.perf_counter() - t0) * 1000),
            result_json["score"],
        )
    except Exception as e:
        err = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        log.error("job.failed id=%s error=%s", claimed.job_id, err.splitlines()[0])
        with session_factory() as session:
            with session.begin():
                mark_failed(session, job_id=claimed.job_id, error_message=err)
    return True


def _is_uuid(s: str) -> bool:
    try:
        uuid.UUID(s)
        return True
    except (ValueError, AttributeError):
        return False


def main() -> int:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL not set")

    init_engine(database_url)
    factory = get_session_factory()
    if factory is None:
        raise SystemExit("failed to init DB engine")

    engine_command = _resolve_engine_command()
    pool_size = _pool_size()
    log.info(
        "starting pool_size=%d engine=%s depth=%d multipv=%d",
        pool_size,
        engine_command,
        _engine_depth(),
        _engine_multipv(),
    )

    shutdown = {"flag": False}

    def _on_signal(signum: int, frame: object) -> None:  # noqa: ARG001
        log.info("signal %d received — graceful shutdown", signum)
        shutdown["flag"] = True

    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    # Use a raw psycopg connection for LISTEN/NOTIFY (SQLAlchemy session
    # doesn't expose the notifications iterator cleanly).
    listen_dsn = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    listen_conn: psycopg.Connection | None = None

    with EnginePool(pool_size=pool_size, command=engine_command) as pool:
        last_heartbeat = time.time()
        try:
            listen_conn = psycopg.connect(listen_dsn, autocommit=True)
            listen_conn.execute(f"LISTEN {_LISTEN_CHANNEL}")
            log.info("listening on channel=%s", _LISTEN_CHANNEL)

            while not shutdown["flag"]:
                # Drain whatever is queued first.
                while _process_one_job(pool, factory):
                    if shutdown["flag"]:
                        break

                if shutdown["flag"]:
                    break

                # Wait for a notification or timeout.
                gen = listen_conn.notifies(timeout=_POLL_INTERVAL_S)
                for _notify in gen:
                    break  # got one — loop back to drain

                now = time.time()
                if now - last_heartbeat >= _HEARTBEAT_S:
                    log.info("heartbeat pool_size=%d", pool_size)
                    last_heartbeat = now
        finally:
            if listen_conn is not None:
                listen_conn.close()
    log.info("worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
