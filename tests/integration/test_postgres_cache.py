"""Integration tests for the Postgres-backed analysis cache.

Feature 008 / T017. Requires a running Postgres (the dev compose service
at port 5432, or the CI `services: postgres` block). Skips cleanly when
`DATABASE_URL` is unset OR Postgres is unreachable.

Coverage:
  - test_double_audit_hits_cache: same PGN twice → second is < 5s
  - test_no_cache_flag_skips_persist: --no-cache doesn't add rows
  - test_db_down_graceful: unreachable Postgres → audit completes
  - test_migration_roundtrip: alembic upgrade head + downgrade base clean
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

REPO_ROOT = Path(__file__).resolve().parents[2]
SMOKE_PGN = REPO_ROOT / "tests" / "fixtures" / "audit_v2_smoke.pgn"
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
        pytest.skip("DATABASE_URL not set — feature 008 integration suite skipped")
    if not _db_available(url):
        pytest.skip(f"Postgres at {url!r} unreachable — integration suite skipped")
    return url


@pytest.fixture(scope="module")
def migrated_db(database_url: str) -> str:
    """Apply alembic upgrade head before tests run."""
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


@pytest.fixture(autouse=True)
def clean_audit_runs(migrated_db: str) -> None:
    """Truncate audit_runs before each test so row-count assertions are
    independent."""
    engine = create_engine(migrated_db)
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE audit_runs"))
    engine.dispose()


def _row_count(url: str) -> int:
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT count(*) FROM audit_runs"))
        row = result.scalar_one()
    engine.dispose()
    return int(row)


def _run_audit(
    pgn_path: Path, env: dict[str, str], extra_args: list[str] | None = None
) -> tuple[int, float]:
    """Spawn `cleanmatch audit-game <pgn>` with the given env. Returns
    (exit_code, wall_clock_seconds)."""
    args = [
        "uv",
        "run",
        "cleanmatch",
        "audit-game",
        str(pgn_path),
        "--output",
        "json",
    ]
    if extra_args:
        args.extend(extra_args)
    # Use static analyzer fallback (no Stockfish/podman in CI) by NOT
    # passing --engine-image. The pipeline's analyzer=None + no
    # engine_command path uses StaticAnalyzer — deterministic + cheap.
    start = time.monotonic()
    result = subprocess.run(  # noqa: S603 — trusted argv
        args,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    elapsed = time.monotonic() - start
    return result.returncode, elapsed


def test_double_audit_hits_cache(migrated_db: str) -> None:
    """Same PGN twice — second call must hit the cache."""
    env = {**os.environ, "DATABASE_URL": migrated_db}
    code1, _ = _run_audit(SMOKE_PGN, env)
    assert code1 == 0, "first audit exited non-zero"
    assert _row_count(migrated_db) == 1, "first run should have inserted exactly 1 row"

    code2, t2 = _run_audit(SMOKE_PGN, env)
    assert code2 == 0, "second audit exited non-zero"
    assert _row_count(migrated_db) == 1, "second run must not insert a duplicate row"
    # Cache hit returns ~immediately. Allow generous budget for Python
    # startup overhead — the cache itself returns in <100ms.
    assert t2 < 10, f"second audit should hit cache, took {t2:.2f}s"


def test_no_cache_flag_skips_persist(migrated_db: str) -> None:
    """With one row cached, --no-cache forces re-analysis without
    inserting another row."""
    env = {**os.environ, "DATABASE_URL": migrated_db}
    # Seed the cache.
    code, _ = _run_audit(SMOKE_PGN, env)
    assert code == 0
    assert _row_count(migrated_db) == 1

    # --no-cache: should not consult or write.
    code, _ = _run_audit(SMOKE_PGN, env, extra_args=["--no-cache"])
    assert code == 0
    assert _row_count(migrated_db) == 1, "--no-cache must not persist"


def test_db_down_graceful(migrated_db: str) -> None:
    """Audit must succeed even when DATABASE_URL points at a dead host."""
    env = {**os.environ, "DATABASE_URL": "postgresql+psycopg://x:y@127.0.0.1:9999/nodb"}
    code, _ = _run_audit(SMOKE_PGN, env)
    assert code == 0, "audit must exit 0 even when DB unreachable"


def test_migration_roundtrip(database_url: str) -> None:
    """alembic upgrade head + alembic downgrade base round-trip cleanly."""
    env = {**os.environ, "DATABASE_URL": database_url}

    # Start from current head (set up by migrated_db fixture in module).
    # Downgrade to base.
    result = subprocess.run(  # noqa: S603 — trusted argv
        ["uv", "run", "alembic", "-c", str(ALEMBIC_INI), "downgrade", "base"],  # noqa: S607 — system uv binary
        env=env,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"downgrade failed:\n{result.stderr}"

    # Then upgrade back to head.
    result = subprocess.run(  # noqa: S603 — trusted argv
        ["uv", "run", "alembic", "-c", str(ALEMBIC_INI), "upgrade", "head"],  # noqa: S607 — system uv binary
        env=env,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, f"re-upgrade failed:\n{result.stderr}"
