# Feature 011 — Handoff Notes

## Context

Feature 011 is **Caminho B Step 1** toward >90% per-account accuracy. See `/home/mestre/.claude/plans/smooth-jumping-lightning.md` for the full roadmap (4 features, ~3-4 months).

## What this feature does

1. Resurrects `timing-analysis` from dead code (parses `[%clk]` from PGNs).
2. Wires a real engine pool (N persistent Stockfish UCI sessions, queued acquire/release).
3. Switches frontend audits from synchronous SSE to async POST + polling via Postgres LISTEN/NOTIFY queue.

## What it does NOT do

- Detection accuracy stays at ~75% per game until **feature 013 ML calibration** lands.
- No multi-tenancy, no auth (deferred to feature 015+).
- No distributed worker pool (single-host MVP; ~100 audits/min ceiling).

## Critical decisions

- Pool size default: `max(2, cpu_count - 2)` — overridable via `CLEANMATCH_POOL_SIZE`.
- Queue tech: PG-LISTEN/NOTIFY (reuses feature 008 Postgres; no new infra dep).
- Frontend: HTTP polling (1 s → 2 s → 4 s backoff), not WebSocket. Polish PR can add WS if needed.
- CLI: keeps synchronous `cleanmatch audit-game` for dev workflows; internally uses pool size=1.

## Blockers / required ops

- **Worker daemon supervision**: `apps/frontend/lib/audit_worker.py` must run as a long-lived process. MVP: run manually. Production: systemd / k8s pod.
- **`alembic upgrade head` required** before frontend can submit audits — schema dependency on `audit_jobs` table.
- Tests skip cleanly when DATABASE_URL is unset or engine_image missing (matches feature 008 pattern).

## Hand-back to roadmap

After feature 011 merges, immediate next step is **feature 012 (chess.com banned-account corpus crawler)** — see roadmap doc. Feature 013 (ML calibration) is gated on feature 012's corpus.
