#!/usr/bin/env python3
"""Worker-health probe for the frontend (feature 012 Camada C).

Returns JSON describing the audit queue + worker liveness so the UI can
show an "worker offline" banner instead of spinning forever on a poll
that will never see status change.

Heuristic:
  worker_alive = True
    if   no row in audit_jobs (clean start, can't tell either way; assume up)
    OR   the queue contains a 'running' row (worker is actively claiming)
    OR   `last_drain` (max finished_at) is within the last 90s
  worker_alive = False
    otherwise — i.e. there are queued rows AND nothing drained in 90s.

Output:
  {"worker_alive": bool,
   "queued": int,
   "running": int,
   "completed_recent": int,   # last 5min
   "last_drain": ISO8601 | null}
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, "/home/mestre/Documents/repositories/clean-match-chess")

from analysis_core.db.session import get_session_factory, init_engine
from sqlalchemy import text


def main() -> int:
    init_engine()
    factory = get_session_factory()
    if factory is None:
        print(json.dumps({"error": "DATABASE_URL not configured"}), flush=True)
        return 1

    try:
        with factory() as session:
            row = session.execute(
                text(
                    """
                    SELECT
                      COUNT(*) FILTER (WHERE status = 'queued')    AS queued,
                      COUNT(*) FILTER (WHERE status = 'running')   AS running,
                      COUNT(*) FILTER (
                        WHERE status = 'completed'
                          AND finished_at > NOW() - INTERVAL '5 minutes'
                      ) AS completed_recent,
                      MAX(finished_at) AS last_drain,
                      EXTRACT(EPOCH FROM (NOW() - MAX(finished_at)))::int AS seconds_since_drain
                    FROM audit_jobs
                    """
                )
            ).one()

        queued = int(row.queued)
        running = int(row.running)
        seconds_since_drain = row.seconds_since_drain  # int | None

        # Default optimistic: no data yet ⇒ can't tell, assume alive.
        worker_alive = True
        if queued > 0:
            # If something queued, worker is alive iff it's actively running
            # OR has drained within the last 90s.
            if running > 0:
                worker_alive = True
            elif seconds_since_drain is None or seconds_since_drain > 90:
                worker_alive = False

        print(
            json.dumps(
                {
                    "worker_alive": worker_alive,
                    "queued": queued,
                    "running": running,
                    "completed_recent": int(row.completed_recent),
                    "last_drain": (row.last_drain.isoformat() if row.last_drain else None),
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
