# Requirements Checklist — Feature 008 (Postgres-backed analysis cache)

**Purpose**: Specification quality gate before `/speckit-implement`.
**Created**: 2026-05-25
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 spec.md has a Context section explaining the why (re-analysis pain + monetization runway)
- [x] CHK002 spec.md has a dated Clarifications section recording the 3 resolved-pre-plan Qs
- [x] CHK003 All user stories carry priorities (USA=P1, USB=P2, USC=P1, USD=P2)
- [x] CHK004 Each user story has Acceptance Scenarios in Given/When/Then form
- [x] CHK005 Edge Cases enumerates ≥ 5 distinct failure modes with mitigations
- [x] CHK006 Each FR / SC carries a numerical identifier (FR-001…FR-008, SC-001…SC-007)
- [x] CHK007 plan.md has Constitution Check with PASS/FAIL per Principle I–IV
- [x] CHK008 plan.md has Technical Context with concrete versions + paths
- [x] CHK009 research.md has decisions D1–D6 with Rationale + Alternatives Considered
- [x] CHK010 tasks.md uses `[X]` / `[P]` markers per repo convention

## Requirement Completeness

- [x] CHK011 Every FR maps to ≥ 1 SC where measurable
- [x] CHK012 No FR contains `[NEEDS CLARIFICATION]` markers
- [x] CHK013 SC values are technology-agnostic + measurable (< 500 ms, exactly 1 row, byte-identical)
- [x] CHK014 Scope boundaries explicit: "No frontend changes", "No users/auth/subscriptions", "No FK constraints" called out
- [x] CHK015 Assumptions stated for: Postgres availability, manifest_hash cost, AuditRun JSON serializability
- [x] CHK016 Constraints stated for: envelope shape stability (FR-007), no hard-fail on DB-down (FR-004), Alembic-only schema changes

## Feature Readiness

- [x] CHK017 Phase 0 — research decisions complete (D1–D6 locked)
- [x] CHK018 Phase 1 — Constitution Check passes; no complexity-tracking entries needed
- [x] CHK019 tasks.md has T001–T026 covering all 7 phases
- [x] CHK020 Critical files enumerated in plan.md "Source Code" tree
- [x] CHK021 Reusable existing code identified (manifest_hash, ReproducibilityManifest, AuditRun.model_dump_json, FPR-gate cache.py shape)
- [x] CHK022 Risk register present in plan file (9 risks + mitigations)
- [x] CHK023 Verification recipe present in `quickstart.md §1-§9`

## Pre-`/speckit-implement` Gate

- [x] CHK024 Plan-mode plan file approved + saved at `/home/mestre/.claude/plans/smooth-jumping-lightning.md`
- [x] CHK025 Branch `008-analysis-cache-postgres` created from `main` via worktree at `/tmp/cmc-008`
- [x] CHK026 Spec scaffold committed (this PR's first commit will include spec.md, plan.md, research.md, tasks.md, quickstart.md, checklists/requirements.md)
- [ ] CHK027 Postgres dep added to packages/analysis-core/pyproject.toml (T004)
- [ ] CHK028 0001_init migration written + verified (T007, T008)
- [ ] CHK029 db/cache.py implemented with graceful degradation (T012)
- [ ] CHK030 Pipeline integration + --no-cache plumbed through (T014, T015, T016)

## Notes

- Items CHK027–CHK030 unchecked because they correspond to in-progress implementation tasks.
- Re-run this checklist after T024 (pytest gate) to confirm SC-006 (CI green against real Postgres).
