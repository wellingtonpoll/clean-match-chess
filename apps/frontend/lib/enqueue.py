#!/usr/bin/env python3
"""Thin shim called by Next.js `POST /api/audit` (feature 011 Phase 3).

Reads `{"pgn_text": str, "subject_color": "white"|"black"}` from stdin,
inserts a row into `audit_jobs` (status='queued'), prints `{"job_id":
"<uuid>"}` to stdout. The Postgres trigger `trg_notify_audit_job_new`
wakes the worker daemon — no polling, no further round-trip.

Errors: any failure (DB down, malformed input, validation) is printed
as `{"error": "..."}` and the script exits 1.
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

from analysis_core.db.audit_jobs import enqueue
from analysis_core.db.session import get_session_factory, init_engine


def main() -> int:
    try:
        payload = json.loads(sys.stdin.read())
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"invalid JSON: {e}"}), flush=True)
        return 1

    pgn_text = payload.get("pgn_text")
    if not isinstance(pgn_text, str) or not pgn_text.strip():
        print(json.dumps({"error": "pgn_text is required"}), flush=True)
        return 1
    subject_color = payload.get("subject_color", "white")

    init_engine()
    factory = get_session_factory()
    if factory is None:
        print(json.dumps({"error": "DATABASE_URL not configured"}), flush=True)
        return 1

    try:
        with factory() as session:
            with session.begin():
                job_id = enqueue(
                    session,
                    pgn_text=pgn_text,
                    subject_color=subject_color,
                )
        print(json.dumps({"job_id": str(job_id)}), flush=True)
        return 0
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
