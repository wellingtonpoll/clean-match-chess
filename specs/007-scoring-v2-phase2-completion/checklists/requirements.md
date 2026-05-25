# Requirements Checklist — Feature 007 (Scoring v2 Phase 2 Completion)

**Purpose**: Specification quality gate before `/speckit-implement` is invoked.

**Created**: 2026-05-25

**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] CHK001 spec.md has a Context section explaining the why (4 deferrals from 005 + new data on disk)
- [x] CHK002 spec.md has a dated Clarifications section recording the 5 resolved-pre-plan Qs
- [x] CHK003 spec.md uses pt-BR-aware language where appropriate; technical terms remain in English
- [x] CHK004 All user stories carry priorities (USA=P1, USB=P1, USC=P1, USD=P2)
- [x] CHK005 Each user story has Acceptance Scenarios in Given/When/Then form (≥3 per P1 story)
- [x] CHK006 Edge Cases section enumerates ≥5 distinct failure modes with mitigations
- [x] CHK007 Each FR / SC carries a numerical identifier (FR-001…FR-010, SC-001…SC-007)
- [x] CHK008 plan.md has Constitution Check with PASS/FAIL per Principle I–IV
- [x] CHK009 plan.md has Technical Context with concrete versions + paths (no NEEDS CLARIFICATION)
- [x] CHK010 research.md has decisions D1–D8 with Rationale + Alternatives Considered
- [x] CHK011 tasks.md uses `[X]` / `[P]` / `[USx]` markers per repo convention

## Requirement Completeness

- [x] CHK012 Every FR maps to ≥ 1 SC (and vice versa where measurable)
- [x] CHK013 No requirement contains "MUST" without a concrete acceptance criterion
- [x] CHK014 No FR contains `[NEEDS CLARIFICATION]` markers
- [x] CHK015 SC values are technology-agnostic + measurable (`fpr ≤ 0.02`, `tpr ≥ 0.80`, etc.)
- [x] CHK016 Scope boundaries explicit: "No scoring algorithm changes" called out in FR-010 and Scope notes
- [x] CHK017 Assumptions stated for: archive integrity, Stockfish reachability, banned-account sourcing, FPR-gate first-run pass, maintainer time budget
- [x] CHK018 Constraints stated for: determinism, gate-threshold relaxation prohibition, schema lock, archive commit prohibition, source restriction to Lichess

## Feature Readiness

- [x] CHK019 Phase 0 — research decisions complete (D1–D8 locked)
- [x] CHK020 Phase 1 — Constitution Check passes; no complexity-tracking entries needed
- [x] CHK021 tasks.md has T001–T025 covering all 6 phases
- [x] CHK022 Critical files enumerated in plan.md "Source Code" tree
- [x] CHK023 Reusable existing code identified (EngineAnalyzer, build_buckets_stub, pgn_loader helpers, fpr_gate harness, manifest fields)
- [x] CHK024 Risk register present in plan.md (8 risks + mitigations)
- [x] CHK025 Verification recipe present in `quickstart.md §10` + `plan.md` Verification block

## Pre-`/speckit-implement` Gate

- [x] CHK026 Plan-mode plan file approved + saved at `/home/mestre/.claude/plans/smooth-jumping-lightning.md`
- [x] CHK027 Branch `007-scoring-v2-phase2-completion` created from `main`
- [x] CHK028 Spec scaffold committed (spec.md, plan.md, research.md, tasks.md, quickstart.md, HANDOFF.md, this checklist) — pending T001 commit
- [ ] CHK029 zstandard dep added (T002)
- [ ] CHK030 SF16 Docker image built locally (T003)

## Notes

- Items CHK029 / CHK030 unchecked because they fall under Phase 1 (T002 / T003), which the maintainer executes after this checklist passes.
- Re-run this checklist after T020 to confirm SC-007 (CHANGELOG state) before opening the PR.
