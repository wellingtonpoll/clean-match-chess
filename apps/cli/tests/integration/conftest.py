"""Shared fixtures for CLI integration tests.

Feature 008 caveat: the integration tests in this directory all use
`monkeypatch.setenv("CLEANMATCH_HOME", str(tmp_path))` to isolate
filesystem artefacts per-test, then read those artefacts back via the
`show` / `export` subcommands. The Postgres analysis cache (feature 008)
is keyed on `(pgn_sha256, manifest_sha256)` only — not on
`CLEANMATCH_HOME` — so a cache hit from a previous test (with a different
tmpdir) would return an `AuditRun` whose `run.id` does NOT correspond to
any file under the CURRENT tmpdir, breaking the show/export path.

Mitigation: disable the cache layer entirely for these tests by clearing
`DATABASE_URL` at fixture-collection time. Tests that need to verify
cache semantics live under `tests/integration/test_postgres_cache.py`
(at the repo root) — those run against a separately-configured fixture.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _disable_db_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Clear DATABASE_URL so feature 008's `db.cache` short-circuits."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    # Reset the cached engine singleton so a previous test's init doesn't
    # leak into this one. Imported here (not at module level) so the
    # conftest stays cheap when feature 008 isn't installed.
    try:
        from analysis_core.db import close_engine

        close_engine()
    except ImportError:
        pass
    yield
