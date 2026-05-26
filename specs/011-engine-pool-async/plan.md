# Implementation Plan — Feature 011

**Branch**: `011-engine-pool-async` | **Spec**: [spec.md](./spec.md)

## Summary

Three phases land sequentially as separate commits but ship in one PR. Each phase has its own unit test gate.

## Phase 1 — Timing extraction (FR-001, FR-002)

**Goal**: `Move.time_spent_ms` populated for every chess.com / Lichess PGN that carries `[%clk]` annotations.

**Files**:
- `packages/analysis-core/src/analysis_core/ingest/pgn_loader.py:162-188` — replace `time_spent_ms=None` hardcode with `_extract_clock_ms(move_node, prior_clock_ms, increment_ms)`.
- `packages/analysis-core/src/analysis_core/ingest/_clock_parser.py` (new) — pure regex parser for `{ [%clk H:MM:SS(.s)] }`. Returns `int | None`.
- `packages/analysis-core/tests/test_pgn_loader.py` — add fixtures with clocks + assert per-move durations.

**Acceptance**:
- 2026-04 chess.com PGN with TimeControl=600+0 → moves have positive `time_spent_ms` summing to ≤ 600000 ms × 2 (one per side).
- PGN without clocks → all moves have `time_spent_ms = None` (existing behavior).
- Increment-aware: TimeControl=600+5 with 30 plies → `sum(time_spent_ms) ≈ wall_clock - 15 increments × 5000 ms × 2 sides`.

## Phase 2 — Engine pool wire-up (FR-003, FR-004)

**Goal**: `EnginePool` holds N persistent UCI sessions, reused across audits.

**Files**:
- `packages/analysis-core/src/analysis_core/engine/stockfish_pool.py` — extend skeleton (`PoolConfig` at lines 30-57) with `EnginePool` class:
  - `__init__(pool_size: int, engine_command: list[str])`
  - `__enter__` / `__exit__` — context-manager spawns N `chess.engine.SimpleEngine.popen_uci` workers + closes them on exit.
  - `acquire()` / `release(worker)` — queue.Queue-backed worker rental, blocks if all busy.
  - `with pool.worker() as engine: engine.analyse(board, …)` — recommended API.
  - `ucinewgame()` between audits to reset transposition table.
- `packages/analysis-core/src/analysis_core/pipeline/run.py:139-156` — `run_single_game` accepts optional `engine_pool: EnginePool | None`. When provided, acquires from pool instead of creating new `EngineAnalyzer`.
- `packages/analysis-core/tests/test_stockfish_pool.py` — new test file:
  - `test_pool_serves_sequential_audits` — 10 audits in a row via pool, all complete.
  - `test_pool_concurrent_acquire_no_deadlock` — N=2 threads, 4 concurrent audits, all complete.
  - `test_pool_ucinewgame_between_audits` — ensures TT doesn't leak between games.
  - `test_pool_graceful_when_engine_unavailable` — skip on engine missing (mirrors feature 008 pattern).

**Acceptance**:
- 10 sequential audits via pool with N=2 finish in ~1.1× the wall time of a single warm audit × 10 (well under 1.5× headroom).
- Pool worker is reused: same `engine.id` (memory address) across multiple `acquire()` calls.

## Phase 3 — Async audit queue (FR-005, FR-006, FR-007, FR-008)

**Goal**: HTTP API accepts audit submissions, returns job_id immediately, worker drains queue via PG-LISTEN.

**Files**:
- `packages/analysis-core/migrations/versions/0003_audit_jobs.py` — new migration:
  - `audit_jobs` table with the schema in FR-005.
  - Trigger `trg_notify_audit_job_new` on INSERT → `NOTIFY audit_jobs_new, NEW.id::text`.
  - Trigger `trg_notify_audit_job_done` on UPDATE WHEN status changed to `completed`/`failed`/`aborted` → `NOTIFY audit_jobs_done, NEW.id::text`.
- `packages/analysis-core/src/analysis_core/db/models.py` — add `AuditJobModel`.
- `packages/analysis-core/src/analysis_core/db/audit_jobs.py` (new) — repository: `enqueue(pgn_text, subject_color) -> uuid.UUID`, `claim_next() -> AuditJobModel | None`, `mark_completed(id, result_json)`, `mark_failed(id, error_message)`, `get_status(id) -> AuditJobModel | None`.
- `apps/frontend/lib/audit_worker.py` (new) — long-running process. Connects via psycopg `connection.add_notify_handler` to `audit_jobs_new`. Pulls one job, runs `run_single_game` with the pool, persists result. Idempotent on duplicate notifications.
- `apps/frontend/app/api/audit/route.ts` (new) — Next.js API route:
  - `POST /api/audit` → calls Python subprocess (`enqueue.py`) which writes to `audit_jobs` and returns `{ job_id }` JSON.
  - `GET /api/audit/[job_id]/route.ts` → polls the DB for that job's status + result.
- `apps/frontend/lib/enqueue.py` (new) — thin Python shim called by the Next.js POST handler. Inserts the audit_jobs row + returns job_id JSON.
- `apps/frontend/app/page.tsx` + `apps/frontend/lib/AnalysisContext.tsx` — change `useEffect` SSE consumer to fetch + setInterval poll on `/api/audit/[job_id]`. Backoff: 1 s → 2 s → 4 s, cap 4 s.

**Acceptance**:
- `POST /api/audit` returns in < 100 ms with a valid job_id.
- Worker process drains queue at the rate the pool can sustain (~5 s per audit with depth=12 multipv=3 and N=4 workers ≈ 20 audits/min).
- 100-job stress test: all 100 jobs reach `completed` status within 30 × wall_clock_per_audit seconds.

## Phase 4 — CLI + integration tests (FR-009)

- `cleanmatch audit-game` stays synchronous (no queue dependency). Internally uses the same `EnginePool` (in-process, N=1) so the timing fix still applies.
- `cleanmatch audit-username` uses the in-process pool with `N=cpu_count-2`, no queue.
- New integration test `tests/integration/test_audit_queue.py` — boots Postgres, enqueues 5 jobs, asserts they all complete with `status='completed'` + non-null `result_json`.

## Phase 5 — Polish + PR

- CHANGELOG.md update.
- `docs/heuristics.md` — document timing signal now active.
- `.env.example` — add `CLEANMATCH_POOL_SIZE` documentation.
- PR vs main with delta table: before/after wall clock per audit, timing signal coverage %.

## Out of scope (this PR)

- Distributed pool across hosts (single-host MVP).
- WebSocket streaming (HTTP polling is fine for MVP).
- Auth on `/api/audit` (feature 015+).
- Timing anomaly re-calibration (feature 013).

## Risks

- **Pool deadlock**: if all N workers crash simultaneously, queue blocks forever. Mitigate with `acquire(timeout=300)` + worker health check on release.
- **PG-LISTEN payload size limit**: chess.com PGNs are < 10 KB, well under Postgres 8 KB NOTIFY limit. But we pass `job_id` only in NOTIFY payload, not the PGN, so this is non-issue.
- **Worker process supervision**: if `audit_worker.py` dies, no one drains. For MVP, run it under systemd / supervisord. For deploy: split into separate container.

## Verification

1. Phase 1: `uv run pytest packages/analysis-core/tests/test_pgn_loader.py -v` passes; spot-check a real chess.com PGN to confirm `Move.time_spent_ms` populated.
2. Phase 2: `uv run pytest packages/analysis-core/tests/test_stockfish_pool.py -v` passes; `time cleanmatch audit-username quaiada --count 5` finishes in ≤ 30 s.
3. Phase 3: `psql -c "SELECT status, COUNT(*) FROM audit_jobs GROUP BY status"` shows all completed after stress test.
4. Phase 4: `tests/integration/test_audit_queue.py` green.
5. Full pytest: 469+ passed, coverage ≥ 85%.
6. Live: open frontend, run audit on quaiada last 10 games. Verify timing-analysis appears in dominant_signals for at least one game.
