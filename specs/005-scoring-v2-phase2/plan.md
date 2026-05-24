# Implementation Plan: Fraud Detection Algorithm v2 — Phase 2 (Empirical Validation & Production Artifacts)

**Branch**: `005-scoring-v2-phase2` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-scoring-v2-phase2/spec.md`

## Summary

Phase 2 closes the four explicit deferrals from `specs/004-scoring-v2-phase1/tasks.md` so the v2.0.0 scoring pipeline can be promoted from `-rc1` to a recommended stable release:

1. **US1 — Production rating baselines**: regenerate `packages/heuristics/data/rating_baselines.json` from the **Lichess Standard month-export 2026-04** by running the existing `packages/heuristics/scripts/build_baselines.py` against the real dataset (currently a hand-curated stub).
2. **US2 — Production opening book**: replace the 1.3 KB stub `packages/analysis-core/data/opening_book.bin` with the canonical `gm2600.bin` (~1 MB+), sha256-verified against the upstream URL recorded in `research.md` R1.
3. **US3 — Labeled-corpus FPR gate**: assemble `tests/fixtures/corpora/{clean,engine_assisted}/` (≥ 50 + ≥ 20 PGNs respectively, with sibling `.provenance.json`), add a CI job that audits every fixture and blocks merge if FPR > 2.0% or TPR < 80.0%, with engine-analysis caching to fit a 5-minute warm budget.
4. **US4 — ReproducibilityManifest reachability**: schema fields (`rating_baselines_sha256`, `signal_versions`) already exist in `packages/shared-types/src/shared_types/report.py`; `build_manifest` already passes them; `manifest.json` on disk already contains them. **Remaining gap (verified during plan)**: `AuditRun` model has no `manifest` field, so the `--output json` envelope does not include manifest provenance in-band. Phase 2 closes this by attaching the persisted manifest to the audit JSON output payload.

**Technical approach**: Phase 2 ships **no algorithm changes** (FR-010). All work is artifact regeneration, corpus assembly, CI infrastructure, and a single targeted JSON-envelope tweak. Dependencies remain stable — no new top-level deps; possible CI-only adds (e.g., GitHub Actions cache plugin, already available). Determinism preserved: bootstrap and CUSUM RNG seeds inherited from Phase 1.

## Technical Context

**Language/Version**: Python 3.12 (CI runner pinned in feature 004 polish; constitution permits 3.11+).

**Primary Dependencies**: Existing — `python-chess`, `pydantic` v2, `numpy` ≥ 2.0 (all from Phase 1). NEW — none at runtime. CI-only — `actions/cache` for engine-analysis cache (GitHub-native, no PyPI dep).

**Storage**: Read-only file inputs replaced — `packages/analysis-core/data/opening_book.bin` grows from 1.3 KB stub to ≥ 1 MB real book; `packages/heuristics/data/rating_baselines.json` regenerated from real Lichess data (size still ≤ 10 KB). New tree: `tests/fixtures/corpora/clean/*.pgn` + `tests/fixtures/corpora/engine_assisted/*.pgn` + sibling `*.provenance.json` files. Estimated total corpus size: ≤ 5 MB (70 PGN × ~50 KB).

**Testing**: `pytest` with hermetic fixtures (unchanged from Phase 1). New test target: `pytest tests/fixtures/corpora/test_fpr_gate.py` (or a Makefile / nox target) that runs the audit pipeline against every corpus fixture and asserts aggregate FPR/TPR. Engine analyses cached at `tests/fixtures/corpora/.cache/<fixture-sha256>.json` (gitignored). CI job uses `actions/cache@v4` to persist the cache between runs.

**Target Platform**: Linux (CI), macOS (developer). Pure Python; no platform-specific code paths.

**Project Type**: Monorepo of Python packages (`packages/`) plus a CLI (`apps/cli`) and a Next.js frontend (`apps/frontend` — out of scope). Phase 2 touches: `packages/heuristics/data/`, `packages/analysis-core/data/`, `tests/fixtures/corpora/` (new), `.github/workflows/ci.yml`, `CHANGELOG.md`, `packages/shared-types/src/shared_types/audit_run.py` (single field add), and `packages/analysis-core/src/analysis_core/pipeline/run.py` (attach manifest to AuditRun).

**Performance Goals** (per constitution Principle IV):
- FPR-gate CI job: ≤ 5 min wall budget on warm cache, ≤ 30 min on cold cache (SC-005).
- No regression in per-game audit time vs Phase 1 (real book + real baselines do not change algorithmic complexity).
- Engine-analysis cache lookup: O(1) per fixture via sha256 keyed JSON file → O(N) total in number of fixtures, no per-ply cost.

**Constraints**: Phase 2 must remain fully offline-capable at audit time (corpus + cache local; only baselines/book download is one-shot maintainer work, not runtime). Audit must still produce reproducible bit-identical scores given the same PGN + engine + seed (SC-007).

**Scale/Scope**: 70 PGN fixtures (50 clean + 20 engine-assisted). Per-game audit times remain Phase 1 baseline. Total CI gate runtime dominated by engine analyses; with cache populated, gate is I/O bound and finishes in seconds.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Code Quality** | PASS | No new modules; one optional field add on `AuditRun` (`manifest: ReproducibilityManifest \| None = None`). Existing `mypy --strict` + `ruff` gates unchanged. No new transitive deps. |
| **II. Testing Standards (NON-NEGOTIABLE)** | PASS | The FPR-gate test target IS the testing artifact for this phase — every Phase 2 deliverable has a measurable test: real baselines validated by schema + sample-size assertion; real book validated by sha256 + book-coverage assertion; FPR-gate test asserts thresholds; manifest field add covered by an `AuditRun` round-trip test. Coverage threshold (85% line / 80% branch) holds; no new uncovered code paths added. |
| **III. UX Consistency** | PASS | CLI flag surface unchanged. JSON output gains one optional field (`manifest`) — additive, not breaking. Exit codes unchanged. The FPR-gate CI job emits a clear human-readable diagnostic on failure (SC-006). |
| **IV. Performance Requirements** | PASS w/ explicit budget | FPR-gate CI job has a documented budget (SC-005: 5 min warm / 30 min cold). Per-game audit time unchanged. Engine-analysis cache hit fast-path is O(1) per fixture. A regression > 10% on warm-cache CI runtime blocks merge per constitution. |

**Constitution gate: PASS**. No violations; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/005-scoring-v2-phase2/
├── plan.md              # This file
├── research.md          # Phase 0: dataset sourcing, book provenance, corpus sourcing strategy, cache design
├── data-model.md        # Phase 1: `.provenance.json` schema, AuditRun.manifest field add
├── quickstart.md        # Phase 1: maintainer steps for refresh-baselines + refresh-book + add-corpus-fixture
├── contracts/
│   ├── provenance.schema.json          # JSON schema for tests/fixtures/corpora/*.provenance.json
│   └── fpr_gate.contract.md            # Shape and semantics of the FPR-gate test output
├── checklists/
│   └── requirements.md                 # Spec quality checklist (already created during /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
clean-match-chess/
├── packages/
│   ├── analysis-core/
│   │   ├── data/
│   │   │   ├── opening_book.bin           # REPLACE 1.3 KB stub with real gm2600.bin (US2)
│   │   │   └── README.md                  # MODIFY — record real upstream URL + sha256 + retrieval date
│   │   └── src/analysis_core/pipeline/
│   │       └── run.py                     # MODIFY — attach persisted manifest to AuditRun (US4)
│   ├── heuristics/
│   │   ├── data/
│   │   │   └── rating_baselines.json      # REGENERATE from Lichess 2026-04 (US1)
│   │   └── scripts/
│   │       └── build_baselines.py         # USE AS-IS (Phase 1 deliverable; runs in maintainer env)
│   └── shared-types/
│       └── src/shared_types/
│           └── audit_run.py               # MODIFY — add optional `manifest: ReproducibilityManifest | None = None` (US4)
├── tests/
│   └── fixtures/
│       └── corpora/                       # NEW (US3)
│           ├── clean/
│           │   ├── *.pgn                  # ≥ 50 verified-clean games
│           │   └── *.provenance.json      # sibling provenance per FR-005
│           ├── engine_assisted/
│           │   ├── *.pgn                  # ≥ 20 Lichess-flagged-account games
│           │   └── *.provenance.json
│           ├── .cache/                    # gitignored — engine-analysis cache keyed by fixture sha256
│           ├── .gitignore                 # NEW — ignore .cache/
│           └── test_fpr_gate.py           # NEW — pytest target asserting FPR ≤ 2.0%, TPR ≥ 80.0%
├── .github/workflows/
│   └── ci.yml                             # MODIFY — add `fpr_gate` job using actions/cache for tests/fixtures/corpora/.cache/
└── CHANGELOG.md                           # MODIFY — record real baselines + book + measured FPR/TPR for v2.0.0
```

**Structure Decision**: Adopt the existing monorepo layout from feature 004 unchanged. The only new top-level tree is `tests/fixtures/corpora/`, chosen over `packages/heuristics/tests/fixtures/corpora/` because the corpus is consumed by an integration CI gate that crosses package boundaries (analysis-core + heuristics + apps/cli) — placing it under a single package would obscure its cross-cutting role.

## Complexity Tracking

No constitution violations. Table omitted.
