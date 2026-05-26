"""Postgres-backed analysis cache for `pipeline.run.run_single_game()`.

Feature 008. Cache key is `(pgn_sha256, manifest_sha256)`:
- `pgn_sha256` content-addresses the input PGN bytes;
- `manifest_sha256` is the output of `analysis_core.manifest.manifest_hash`,
  which covers engine binary, opening book, baselines, signal versions,
  scoring threshold version — so an algorithm bump invalidates every row
  automatically without manual purges.

The cache gracefully degrades when `DATABASE_URL` is unset or Postgres is
unreachable: lookup returns `None`, persist no-ops, and a structured
warning lands on stderr. The audit pipeline runs at full cost in that case
but does not fail.
"""

from analysis_core.db.cache import lookup, persist
from analysis_core.db.models import AuditRunModel, Base
from analysis_core.db.session import (
    close_engine,
    get_session_factory,
    init_engine,
)

__all__ = [
    "AuditRunModel",
    "Base",
    "close_engine",
    "get_session_factory",
    "init_engine",
    "lookup",
    "persist",
]
