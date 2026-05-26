# Tasks — Feature 011

## Phase 1 — Timing extraction

- [ ] **T001** Create `packages/analysis-core/src/analysis_core/ingest/_clock_parser.py` — pure regex parser for `{ [%clk H:MM:SS(.s)] }`. Pure function `parse_clock(comment: str) -> int | None` returning ms.
- [ ] **T002** Add unit tests at `packages/analysis-core/tests/test_clock_parser.py` — cover `1:23:45`, `0:00:30`, `0:00:30.5`, `[%clk` only, malformed, empty.
- [ ] **T003** Modify `packages/analysis-core/src/analysis_core/ingest/pgn_loader.py:162-188` — pass prior clock + increment + parse current comment via `_clock_parser`. Populate `Move.time_spent_ms`.
- [ ] **T004** Extend `packages/analysis-core/tests/test_pgn_loader.py` with 2 fixtures: (a) chess.com-style PGN with `[%clk]` comments + TC=600+0, (b) Lichess-style PGN with `[%clk]` + TC=180+1. Assert per-move ms.
- [ ] **T005** Smoke test against live chess.com PGN (quaiada): confirm `time_spent_ms > 0` on > 80% of moves.

## Phase 2 — Engine pool

- [ ] **T006** Extend `packages/analysis-core/src/analysis_core/engine/stockfish_pool.py` — `EnginePool` class with `__init__(pool_size, engine_command)`, `__enter__`, `__exit__`, `worker()` context manager. Uses `queue.Queue` for thread-safe rental. `ucinewgame()` between audits.
- [ ] **T007** Unit tests at `packages/analysis-core/tests/test_stockfish_pool.py` — sequential audits, concurrent acquire, TT reset, graceful skip on engine unavailable.
- [ ] **T008** Modify `packages/analysis-core/src/analysis_core/pipeline/run.py:139-156` — `run_single_game` accepts optional `engine_pool: EnginePool | None`. When set, acquires worker; else falls back to per-audit `EngineAnalyzer` (existing path).
- [ ] **T009** Add benchmark `packages/analysis-core/benchmarks/bench_engine_pool.py` — measure 10 sequential audits with vs. without pool. Asserts pool is ≥ 5× faster on warm path.

## Phase 3 — Async audit queue

- [ ] **T010** Migration `packages/analysis-core/migrations/versions/0003_audit_jobs.py` — `audit_jobs` table + 2 triggers (`trg_notify_audit_job_new`, `trg_notify_audit_job_done`).
- [ ] **T011** Add `AuditJobModel` to `packages/analysis-core/src/analysis_core/db/models.py`.
- [ ] **T012** Repository module `packages/analysis-core/src/analysis_core/db/audit_jobs.py` — `enqueue`, `claim_next`, `mark_completed`, `mark_failed`, `get_status`. Mirror baseline_store pattern from feature 007.
- [ ] **T013** Unit tests `packages/analysis-core/tests/test_audit_jobs.py` — claim concurrency (FOR UPDATE SKIP LOCKED), state transitions, idempotency.
- [ ] **T014** Worker daemon `apps/frontend/lib/audit_worker.py` — long-running process. Connects via psycopg, `LISTEN audit_jobs_new`. Pulls job, runs audit via pool, persists result. Heartbeat to stderr every 30s.
- [ ] **T015** Next.js API routes:
  - `apps/frontend/app/api/audit/route.ts` — POST handler. Spawns Python subprocess `apps/frontend/lib/enqueue.py` which inserts the job + returns `{ job_id }`.
  - `apps/frontend/app/api/audit/[job_id]/route.ts` — GET handler. Polls the DB via `apps/frontend/lib/get_audit_status.py` (Python subprocess).
- [ ] **T016** Frontend integration — `apps/frontend/lib/AnalysisContext.tsx`: change SSE consumer to POST + setInterval poll on `/api/audit/[job_id]`. Backoff: 1 s, 2 s, 4 s.
- [ ] **T017** Integration test `tests/integration/test_audit_queue.py` — boots Postgres, enqueues 5 jobs, polls until all complete, asserts non-null result_json.

## Phase 4 — CLI + integration

- [ ] **T018** Modify `apps/cli/src/cleanmatch_cli/commands/audit_game.py` — internally use `EnginePool(pool_size=1)` so the timing parser fix flows through.
- [ ] **T019** Modify `apps/cli/src/cleanmatch_cli/commands/audit_username.py` — use `EnginePool(pool_size=cpu_count-2)` for the batch; reuse across games.
- [ ] **T020** Smoke test `cleanmatch audit-username quaiada --count 10` — finishes in ≤ 1.5× the time of a single warm audit × 10.

## Phase 5 — Polish + PR

- [ ] **T021** Update CHANGELOG.md `[Unreleased]` block with feature 011 entry.
- [ ] **T022** Update `docs/heuristics.md` — timing-analysis now functional; document threshold + signal weight.
- [ ] **T023** Update `.env.example` — add `CLEANMATCH_POOL_SIZE` documentation.
- [ ] **T024** Run full pytest + coverage gate. Run ruff check / format / mypy.
- [ ] **T025** Open PR vs main with before/after delta table (timing signal coverage %, wall clock per audit).
