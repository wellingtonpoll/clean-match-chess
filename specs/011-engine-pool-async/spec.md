# Feature 011 — Engine Pool, Timing Extraction, and Async Audit Queue

**Branch**: `011-engine-pool-async` | **Status**: Active | **Owner**: cleanmatch

## Why

The audit pipeline today (post features 008-010):

1. **Spawns a fresh Stockfish container per audit.** `cleanmatch audit-game` → `EngineAnalyzer.__enter__` → `podman run --rm -i cleanmatch-stockfish:sf16`. With ~2-5 s container startup overhead, 100 concurrent users × 10 games = 1000 container spawns, ~100 GB transient RAM, hours of cumulative startup waste. **Not production-viable.**
2. **Discards timing data at PGN ingestion.** `pgn_loader.py:179` hardcodes `time_spent_ms=None`. Per-move clock annotations `{ [%clk H:MM:SS] }` are present in 100% of chess.com / Lichess online PGNs but never parsed. The `timing_analysis` heuristic (`heuristics/timing_analysis/__init__.py`) consequently silences itself on every real audit (signal `samples=0`). One of the strongest single-game cheat indicators is dead code.
3. **Serves audits synchronously** — frontend SSE streams while the worker blocks for the full Stockfish run. Connection drops mid-audit lose the work. No retry, no queue, no horizontal scale.

This is the first feature on the [Caminho B roadmap](../../../.claude/plans/smooth-jumping-lightning.md) toward >90% per-account detection accuracy. Without (1) and (2) fixed, features 012/013/014 (corpus + ML calibration + multi-game pooling) have nothing solid to build on.

## Functional Requirements

- **FR-001**: `pgn_loader.load_pgn_path` / `load_pgn_text` MUST extract per-move clock annotations and populate `Move.time_spent_ms` for every move whose PGN contains `{ [%clk H:MM:SS(.s)] }` syntax (per the chess.com / Lichess de-facto standard). When clocks are absent, `time_spent_ms` remains `None` (existing behavior).
- **FR-002**: When a PGN's `TimeControl` header carries an increment (e.g., `600+5`), `time_spent_ms` MUST be the wall-clock duration on the player's clock MINUS the increment that was granted at the start of the move. Negative values clamp to 0.
- **FR-003**: A new `EnginePool` class in `packages/analysis-core/src/analysis_core/engine/stockfish_pool.py` MUST hold N persistent Stockfish UCI sessions, acquire/release them safely under concurrent load, and survive worker idle periods without dropping the UCI connection. N is configurable via `CLEANMATCH_POOL_SIZE` env var (default: `max(2, cpu_count - 2)`).
- **FR-004**: `pipeline.run.run_single_game` MUST acquire a worker from the pool, run analysis through `position` + `go depth N` UCI commands, and release the worker. No `podman run` between game audits within one process.
- **FR-005**: A new `audit_jobs` Postgres table MUST hold `(id UUID PK, pgn_sha256 BYTEA, manifest_sha256 BYTEA, status VARCHAR, result_json JSONB, error_message TEXT, created_at TIMESTAMPTZ, started_at, finished_at)` with the same `status` state machine semantics as `baseline_runs` (`queued → running → completed | failed | aborted`). Migration `0003_audit_jobs.py`.
- **FR-006**: A new `POST /api/audit` HTTP endpoint MUST accept `{ pgn_text: str, subject_color?: 'white'|'black' }`, INSERT one row into `audit_jobs` with status='queued', and return `{ job_id }` synchronously without blocking on Stockfish.
- **FR-007**: Worker process(es) listening on `LISTEN audit_jobs_new` MUST dequeue ready jobs via `SELECT … FOR UPDATE SKIP LOCKED`, run the full audit pipeline, persist the resulting `AuditRun` JSON to `audit_jobs.result_json`, and `NOTIFY audit_jobs_done` with the job id. Worker is the same Python process as the frontend's `analyze.py` is today, just listening on a channel instead of reading stdin.
- **FR-008**: A new `GET /api/audit/{job_id}` HTTP endpoint MUST return `{ status, result?, error? }` reading from `audit_jobs`. Frontend polls this every 1-2 s OR opens a WebSocket on `/api/audit/{job_id}/stream` (latter is optional polish).
- **FR-009**: `cleanmatch audit-game` CLI command MUST keep working synchronously (no queue dependency) so dev / hermetic workflows continue. Adds an optional `--pool-via=local|remote` flag (default: `local` for in-process pool reuse).

## Non-Functional Requirements

- **NFR-001** (Performance): With `CLEANMATCH_POOL_SIZE=4`, 100 sequential audits MUST complete in ≤ 1.2× the time it takes to audit them in a single hot Stockfish session. (Headroom: queue + UCI overhead, but no per-audit container spawn.)
- **NFR-002** (Determinism): Same PGN audited twice through the pool MUST produce identical `score` + `dominant_signals`. UCI session state (TT, history) must reset between audits via `ucinewgame`.
- **NFR-003** (Test isolation): `EnginePool` MUST be optional-importable in unit tests (graceful degrade when podman / Stockfish unavailable). Tests inject `StaticAnalyzer` explicitly, same as today.
- **NFR-004** (Manifest correctness): `Move.time_spent_ms` populated by FR-001/002 MUST flow through `audit_run.run_json` into the persisted Postgres cache so re-audits with the same `(pgn_sha256, manifest_sha256)` produce identical results.

## Success Criteria

- **SC-001**: `timing-analysis` signal returns `samples > 0` on ≥80% of real chess.com PGNs (today: 0%).
- **SC-002**: `cleanmatch audit-username quaiada --count 10` finishes in ≤ 1.5× the time of a single warm audit × 10. Today: ~60 s per game = 10 min. Target: ~5 s warm × 10 = ~50 s, allow up to ~75 s.
- **SC-003**: FPR-gate (`tests/fpr_gate/test_fpr_gate.py`) runs end-to-end against the engine-pooled pipeline without falling back to `StaticAnalyzer`. Run.json includes a non-zero `engine.binary_sha256`.
- **SC-004**: 100-job stress test against `POST /api/audit` completes with 0 dropped jobs; all 100 visible via `GET /api/audit/{id}` within 30 s of submission.

## Out of Scope (deferred to future features)

- Distributed engine pool across multiple hosts (single-host MVP first).
- Authentication on `POST /api/audit` (feature 015+ multi-tenancy).
- WebSocket streaming for result delivery (HTTP polling is acceptable for MVP; WebSocket is polish).
- Engine-invariance: normalizing depth-12 vs depth-18 evals to a canonical depth (handled in feature 013 ML calibration).
- Timing-anomaly threshold re-calibration (handled in feature 013 with labeled corpus).

## Constraints

- Postgres 17+ (already provisioned by feature 008 infra)
- chess.com pub API stays read-only; no auth
- python-chess 1.999+ for UCI session management
- Engine pool MUST NOT pin host CPU above 80% under load — N=cpu_count-2 default leaves headroom for OS + frontend
- Postgres `audit_jobs.result_json` JSONB column avoids dedup since each audit has unique `(pgn_sha256, manifest_sha256, started_at)` — runs with identical hash still hit feature 008 cache (cheap)

## Links

- Plan: [plan.md](./plan.md)
- Tasks: [tasks.md](./tasks.md)
- Research: [research.md](./research.md)
- Quickstart: [quickstart.md](./quickstart.md)
- Roadmap context: [../../../.claude/plans/smooth-jumping-lightning.md](../../../.claude/plans/smooth-jumping-lightning.md)
