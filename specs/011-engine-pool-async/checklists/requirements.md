# Requirements Checklist — Feature 011

## Functional

- [ ] **FR-001** `pgn_loader` extracts `[%clk]` annotations → `Move.time_spent_ms`
- [ ] **FR-002** Increment-aware: `time_spent_ms` accounts for TC increment
- [ ] **FR-003** `EnginePool` holds N persistent UCI sessions, env-configurable
- [ ] **FR-004** `run_single_game` uses pool when provided
- [ ] **FR-005** `audit_jobs` migration + table + 2 triggers (NEW + DONE)
- [ ] **FR-006** `POST /api/audit` returns `{ job_id }` synchronously
- [ ] **FR-007** Worker daemon LISTENs + claims via SKIP LOCKED + persists result
- [ ] **FR-008** `GET /api/audit/{job_id}` returns status + result
- [ ] **FR-009** `cleanmatch audit-game` keeps sync mode

## Non-functional

- [ ] **NFR-001** 100 sequential audits ≤ 1.2× a single warm session × 100
- [ ] **NFR-002** Deterministic: same PGN twice → same score (ucinewgame reset)
- [ ] **NFR-003** Tests skip cleanly when engine unavailable
- [ ] **NFR-004** `Move.time_spent_ms` flows through `run_json` → DB cache

## Success criteria

- [ ] **SC-001** `timing-analysis.samples > 0` on ≥ 80% real chess.com PGNs
- [ ] **SC-002** `audit-username --count 10` ≤ 1.5× single warm × 10
- [ ] **SC-003** FPR-gate runs against real engine pool, not StaticAnalyzer
- [ ] **SC-004** 100-job stress test: 0 dropped, all visible in `GET /api/audit/{id}` within 30 s
