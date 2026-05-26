# Research — Feature 011

## R1. Stockfish UCI session reuse (engine pool)

**Question**: Can a single Stockfish process safely serve N sequential audits without restart?

**Answer**: Yes. UCI protocol explicitly supports session reuse:
- `ucinewgame` resets transposition table + history heuristics. MUST be sent between independent games.
- `position fen <FEN>` or `position startpos moves <moves>` sets new state.
- `go depth <N>` triggers search; result via `info` + `bestmove`.

python-chess `SimpleEngine.popen_uci()` keeps the subprocess open. Calling `engine.analyse(board, limit)` repeatedly reuses the same process — `ucinewgame` is sent internally when the board reset is detected. Verified by reading python-chess source.

**Implication**: Pool of N persistent `SimpleEngine` instances is straightforward. queue.Queue arbitrates acquire/release.

## R2. PG-LISTEN/NOTIFY for queue

**Question**: Is PG-LISTEN/NOTIFY a viable lightweight job queue for ~100 audits/min?

**Answer**: Yes for this scale.
- NOTIFY payload limit: 8000 bytes (`max_notify_queue_pages` x page_size). We only pass `job_id` (~36 bytes for UUID), well under.
- LISTEN consumers receive on COMMIT of the inserting transaction. Workers block on `psycopg connection.notifies()` iterator with `poll_timeout=N` for backoff.
- Trade-off vs Redis: PG-LISTEN reuses the Postgres we already have (feature 008). Redis adds another service. For MVP (single-host), PG-LISTEN wins on simplicity.
- For multi-host scale (1k+ audits/min, 10+ workers): switch to Redis Streams or RabbitMQ. Out of scope for feature 011.

**Implication**: Migration adds 2 triggers (NEW on INSERT, DONE on UPDATE). Worker uses `psycopg.Connection.notifies()`.

## R3. chess.com / Lichess clock annotation format

**Question**: What exact format do chess.com and Lichess emit for per-move clocks?

**Answer**: Both use the PGN comment `{ [%clk H:MM:SS(.s)] }` per the de-facto standard.

Examples from quaiada games (chess.com):
- `1. e4 {[%clk 0:09:55]} e5 {[%clk 0:09:58]} 2. Nf3 {[%clk 0:09:54]}`
- Sub-second variant: `{[%clk 0:09:55.5]}`

Lichess emits the same — also includes `[%eval -0.23]` annotations sometimes, which we ignore for now (feature 013 may use for engine-invariance verification).

**Regex**: `r'\[%clk\s+(\d+):(\d+):(\d+)(?:\.(\d+))?\]'`. Capture H, M, S, optional decimal.

`time_spent_ms` computation (per FR-002):
```
delta_ms = prior_clock_ms - current_clock_ms
spent = max(0, delta_ms + increment_ms)  # increment is added BEFORE the move starts
```

Special case: **first move of each side** has no prior clock → use `TimeControl.initial_seconds * 1000` as prior.

## R4. Engine pool size sizing

**Question**: What pool size is optimal?

**Answer**: `max(2, cpu_count - 2)`:
- Each Stockfish worker is configured `Threads=1` (determinism for baselines + audits).
- Leaves 2 cores for OS + frontend Python + Postgres.
- On a 6-core Ryzen 5500 (12 threads w/ SMT): pool_size=4 leaves 8 threads for everything else.
- Override via `CLEANMATCH_POOL_SIZE=N` env var for tuning.

Memory: each Stockfish with Hash=256MB = ~340 MB / worker. 4 workers = ~1.4 GB. Fits within typical dev box; for prod, add headroom.

## R5. Frontend SSE → polling migration

**Question**: Why polling instead of WebSocket?

**Answer**: Polling chosen for MVP simplicity:
- WebSocket requires duplex connection management, reconnect logic, server-side broadcast. More code.
- Polling with 1-2 s interval is acceptable UX for audits taking 5-30 s. User sees "running…" then "done in 8s".
- HTTP/1.1 keep-alive amortizes TCP cost across multiple polls.
- WebSocket can land in a polish PR if needed.

Backoff strategy: 1 s → 2 s → 4 s, capped at 4 s. Total polls for a 30 s audit: ~9 requests, ~1-2 KB each. Negligible bandwidth.

## R6. `cleanmatch audit-game` synchronous mode

**Question**: Should CLI continue spawning per-audit engine, or use pool?

**Answer**: Internal pool, single worker. The CLI is single-shot from the user's perspective but using `EnginePool(pool_size=1)` ensures (a) the timing parser fix from Phase 1 reaches the same code path, (b) the audit pipeline behaves identically whether invoked via CLI or via worker daemon.

No `--pool-via=remote` mode — that would require a separate worker daemon running for the CLI to dispatch to, which is over-engineering for a maintainer-side debug tool.

## R7. Worker process supervision

**Question**: How to keep `audit_worker.py` alive?

**Answer**: Out of scope for feature 011, but documented for production:
- **MVP local**: run manually `python apps/frontend/lib/audit_worker.py` in a separate terminal. Frontend dev expects this.
- **Production**: systemd unit, kubernetes pod with restart policy, or supervisord. Same pattern as feature 008 docs.
- **Scale**: multiple worker processes can LISTEN on the same channel; FOR UPDATE SKIP LOCKED ensures each job claimed exactly once.

## Decisions locked

- D1/R1: Pool persistent UCI sessions (not respawn).
- D2/R2: PG-LISTEN/NOTIFY (not Redis) for queue.
- D3/R3: chess.com / Lichess clock format via single regex.
- D4/R4: Pool size = max(2, cpu_count-2) default.
- D5/R5: HTTP polling (not WebSocket) frontend.
- D6/R6: CLI uses in-process pool size=1.
- D7/R7: Worker supervision out of scope (run by hand for MVP).
