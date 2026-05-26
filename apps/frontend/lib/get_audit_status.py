#!/usr/bin/env python3
"""Thin shim called by Next.js `GET /api/audit/[job_id]` (feature 011 Phase 3).

Reads `{"job_id": "<uuid>"}` from stdin (or argv[1] as fallback), looks
up the row in `audit_jobs`, prints the status JSON to stdout.

Response shape:
  {"job_id": "<uuid>", "status": "queued"|"running"|"completed"|"failed"|"aborted",
   "result": {...} | null, "error": "..." | null, "audit_run_id": "<uuid>" | null}

`status: "not_found"` is returned for an unknown job_id, with exit 0.
"""

from __future__ import annotations

import json
import sys
import uuid

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

from analysis_core.db.audit_jobs import get_status
from analysis_core.db.session import get_session_factory, init_engine


def main() -> int:
    job_id_raw: str | None = None
    if len(sys.argv) >= 2:
        job_id_raw = sys.argv[1]
    else:
        try:
            payload = json.loads(sys.stdin.read() or "{}")
            job_id_raw = payload.get("job_id")
        except json.JSONDecodeError:
            pass

    if not job_id_raw:
        print(json.dumps({"error": "job_id required"}), flush=True)
        return 1
    try:
        job_id = uuid.UUID(job_id_raw)
    except ValueError:
        print(json.dumps({"error": f"invalid job_id: {job_id_raw}"}), flush=True)
        return 1

    init_engine()
    factory = get_session_factory()
    if factory is None:
        print(json.dumps({"error": "DATABASE_URL not configured"}), flush=True)
        return 1

    try:
        with factory() as session:
            status = get_status(session, job_id=job_id)
        if status is None:
            print(
                json.dumps(
                    {
                        "job_id": str(job_id),
                        "status": "not_found",
                        "result": None,
                        "error": None,
                        "audit_run_id": None,
                    }
                ),
                flush=True,
            )
            return 0
        print(
            json.dumps(
                {
                    "job_id": str(status.job_id),
                    "status": status.status,
                    "result": status.result_json,
                    "error": status.error_message,
                    "audit_run_id": (str(status.audit_run_id) if status.audit_run_id else None),
                }
            ),
            flush=True,
        )
        return 0
    except Exception as e:
        print(json.dumps({"error": f"{type(e).__name__}: {e}"}), flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
