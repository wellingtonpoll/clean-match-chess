---
description: "Task list for feature 005 — Fraud Detection Algorithm v2 (Phase 2)"
---

# Tasks: Fraud Detection Algorithm v2 — Phase 2 (Empirical Validation & Production Artifacts)

**Input**: Design documents from `/specs/005-scoring-v2-phase2/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — constitution Principle II (Testing Standards is NON-NEGOTIABLE). Every new data path (provenance loader, manifest attachment, FPR computation) gets unit tests; the FPR gate itself is the integration test for the corpus.

**Organization**: Tasks grouped by user story. Phase 2 ships **no algorithm changes** (FR-010). All work is artifact regeneration, corpus assembly, CI infrastructure, and one targeted JSON-envelope tweak.

**Path deviation note (implementation)**: Gate utility code referenced as `tests/fixtures/corpora/_provenance_loader.py`, `_engine_cache.py`, `_fpr_gate.py`, and `test_fpr_gate.py` in original task descriptions was actually implemented under `tests/fpr_gate/` (`provenance.py`, `cache.py`, `gate.py`, `test_fpr_gate.py`). Justification: `tests/fixtures/` is excluded by `ruff` and not on the `mypy` files list (it holds data, not code), and lint/type strictness is constitutional (Principle I). PGN corpus + `.provenance.json` siblings stay at `tests/fixtures/corpora/{clean,engine_assisted}/`; only Python utilities moved.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Includes exact file paths in descriptions

## Path Conventions

Monorepo of Python packages under `packages/` plus apps under `apps/` plus repo-root `tests/`. Paths below are repo-relative.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Scaffold the corpus tree, gitignore the engine-analysis cache, and document upstream sources.

- [X] T001 Create directories `tests/fixtures/corpora/clean/` and `tests/fixtures/corpora/engine_assisted/` and `tests/fixtures/corpora/.cache/`. Add `tests/fixtures/corpora/.gitignore` with content `/.cache/` so the engine-analysis cache is never committed. Commit empty trees with `.gitkeep` files in `clean/` and `engine_assisted/`; T013 and T021 must `rm` the matching `.gitkeep` when they land the first real fixture.
- [X] T002 [P] Update `packages/analysis-core/data/README.md` with a placeholder section "Phase 2 will populate this with the real gm2600.bin sha256, source URL, and retrieval date" so T012 has a target file structure to edit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Tiny set of pre-work so user stories can run in parallel.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 [P] Add `jsonschema >= 4.0` to `packages/heuristics/pyproject.toml` `[project.optional-dependencies].test` (or `dev` group) if not already present; run `uv sync` from repo root. Required by T005 (provenance schema validation) and the FPR-gate test.
- [X] T004 [P] Create `specs/005-scoring-v2-phase2/checklists/.gitkeep` if the `checklists/` directory is empty so the spec dir layout is committable. (Spec checklist file already exists from `/speckit-specify` step — verify before adding gitkeep.)
- [X] T005 [depends on T003] Create `tests/fixtures/corpora/_provenance_loader.py` — small utility module with two public functions: `load_provenance(pgn_path: Path) -> ProvenanceRecord` (reads sibling `<stem>.provenance.json`, validates against `specs/005-scoring-v2-phase2/contracts/provenance.schema.json`, returns a typed pydantic model) and `iter_corpus(root: Path) -> Iterable[tuple[Path, ProvenanceRecord]]`. The pydantic `ProvenanceRecord` model lives in this same file (not in shared-types) per data-model.md §5.
- [X] T006 [P] Add `tests/fixtures/corpora/test_provenance_loader.py` — unit tests covering: (a) valid clean-fixture provenance loads; (b) valid engine_assisted-fixture provenance loads; (c) missing sibling file → clear error; (d) invalid `label` enum → schema validation error with field path in message; (e) `iter_corpus` discovers both subdirs and skips non-PGN siblings. Tests run against synthetic mini-fixtures under `tests/fixtures/corpora/_smoke/` (created in this task, gitignored from FPR-gate discovery but committed for test reproducibility).

**Checkpoint**: Foundation ready — user stories US1, US2, US3, US4 can begin in parallel.

---

## Phase 3: User Story 1 - Production Rating Baselines from Real Lichess Data (Priority: P1)

**Goal**: Regenerate `packages/heuristics/data/rating_baselines.json` from the Lichess Standard 2026-04 month-export.

**Independent Test**: After regeneration, every bucket has `sample_size ≥ 1000`; `source_dataset` references the real URL + date; the smoke-test audit's `manifest.rating_baselines_sha256` differs from the Phase 1 stub value.

### Implementation for User Story 1

- [ ] T007 [US1] Download `https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst` to `/tmp/lichess_2026-04.pgn.zst` and decompress to `/tmp/lichess_2026-04.pgn` using `zstd -d`. Record the downloaded archive's sha256 in scratch notes for the T010 commit message. If 2026-04 is unavailable (per FR-001 fallback clause), substitute the most recent prior complete month and document the substitution in the `source_dataset` field at T008.
- [ ] T008 [US1, depends on T007] Run `uv run python packages/heuristics/scripts/build_baselines.py --input /tmp/lichess_2026-04.pgn --output packages/heuristics/data/rating_baselines.json --source-label "lichess_db_standard_rated_2026-04"`. Expect 30-90 min runtime. Commit ONLY the resulting JSON (not the raw Lichess PGN).
- [ ] T009 [US1, depends on T008] Verify the new JSON: load via `from heuristics.rating_baselines import get_baselines`; assert every `bucket.sample_size >= 1000`; assert `source_dataset` contains `"lichess_db_standard_rated_2026-04"`; assert schema validation passes (per `packages/heuristics/contracts/rating_baselines.schema.json`). Add this verification as a one-shot unit test `packages/heuristics/tests/test_real_baselines_smoke.py` that runs in CI but skips if the file's `source_dataset` still references `"hand-curated-stub"` (graceful for branches where T008 hasn't yet landed).
- [ ] T010 [US1, depends on T008] Capture pre-Phase-2 baseline scores for delta documentation:

  ```bash
  cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/baseline_pre_phase2.json
  jq '.score.score, .manifest.rating_baselines_sha256' /tmp/baseline_pre_phase2.json
  ```

  Stash both values in scratch notes. After T008 + T013 land, repeat → `/tmp/baseline_post_phase2.json`. The delta + new sha256 go into the CHANGELOG entry at T034.

**Checkpoint**: US1 functional; real baselines installed and verified.

---

## Phase 4: User Story 2 - Production Opening Book Verified Against Upstream (Priority: P1)

**Goal**: Replace the 1.3 KB stub `opening_book.bin` with the canonical `gm2600.bin`, sha256-verified.

**Independent Test**: New file ≥ 1 MB; sha256 matches the value recorded in `packages/analysis-core/data/README.md`; smoke-test PGN's first ≥ 12 plies flagged `is_book = True`.

### Implementation for User Story 2

- [ ] T011 [US2] Download `gm2600.bin` from `https://github.com/michaelb/Sayuri-chess-bot/raw/main/books/gm2600.bin` (or equivalent mirror — record the exact URL used). Compute sha256: `sha256sum /tmp/gm2600.bin`. If a mirror is used, the sha256 MUST match the canonical value recorded by any prior maintainer; if no prior canonical value exists, this download establishes it.
- [ ] T012 [US2, depends on T011] Copy `/tmp/gm2600.bin` to `packages/analysis-core/data/opening_book.bin` (overwriting the stub) and update `packages/analysis-core/data/README.md` to record: (a) source URL used in T011; (b) retrieval date (ISO 8601); (c) sha256 from T011; (d) one-line provenance note. Replace the Phase 1 stub README content entirely.
- [ ] T013 [US2, depends on T012] Add unit test `packages/analysis-core/tests/test_real_book_coverage.py` — load the book via `OpeningBook.load()`; walk the smoke-test PGN (`tests/fixtures/audit_v2_smoke.pgn`); assert that ≥ 12 of the first 16 plies have `book.contains(board) == True`. The test skips gracefully if the file size is still ≤ 100 KB (Phase 1 stub) so branches without T012 don't fail it.

**Checkpoint**: US2 functional; real book installed; coverage verified.

---

## Phase 5: User Story 3 - False-Positive-Rate Gate Against Labeled Corpus (Priority: P1)

**Goal**: Assemble the labeled corpus, build the FPR-gate test target, wire the CI job, enforce thresholds.

**Independent Test**: The gate test PASSES on the shipped corpus (FPR ≤ 2.0%, TPR ≥ 80.0%); a synthetic regression PR that biases clean-corpus scores up by 0.3 is BLOCKED with a clear diagnostic (per SC-006).

### Tests for User Story 3

- [X] T014 [P] [US3] Write `tests/fixtures/corpora/test_fpr_gate_unit.py` — unit tests for the gate's internal computations (NOT yet exercising the full corpus): (a) classification correctness for FP/FN/TP/TN given a synthetic mock AuditRun + label pairs; (b) 95% exact-binomial CI computation against a reference table; (c) diagnostic JSON shape matches `contracts/fpr_gate.contract.md`; (d) cache key derivation is stable across runs given the same inputs; (e) graceful handling of corpus with zero fixtures (skip, not crash); (f) **cache hit/miss semantics in `_engine_cache.py`**: save→load round-trip is byte-identical; load on missing key returns None; load on engine/book sha256 mismatch (per F3) raises a clear error.
- [X] T015 [P] [US3] Write `tests/fixtures/corpora/test_fpr_gate_smoke.py` — smoke test that the gate orchestration code runs end-to-end on the mini synthetic corpus under `tests/fixtures/corpora/_smoke/` (created in T006) without needing a real engine, by stubbing the audit-pipeline call to return canned `AuditRun` objects. Asserts pass/fail behavior given crafted score distributions.

### Implementation for User Story 3

- [X] T016 [US3, depends on T005] Create `tests/fixtures/corpora/_engine_cache.py` — small utility for the engine-analysis cache. Public API: `cache_path(fixture_pgn: Path) -> Path` (returns `tests/fixtures/corpora/.cache/<sha256(pgn_bytes)>.json`), `load_cached(fixture_pgn: Path, *, expected_engine_sha256: str, expected_book_sha256: str) -> AuditRun | None`, `save_cached(fixture_pgn: Path, run: AuditRun) -> None`. Each cache JSON embeds the `engine_binary_sha256` + `opening_book_sha256` from the AuditRun's manifest. On load, if either sha256 differs from the `expected_*` passed by the caller, `load_cached` returns None (cache miss — forces re-analysis) and emits a warning. This prevents stale-cache bugs when a developer locally swaps the engine or book without busting `.cache/` (closes F3). Uses `model_dump_json` / `model_validate_json` so reloads are byte-identical when sha256 checks pass.
- [X] T017 [US3, depends on T016] Create `tests/fixtures/corpora/_fpr_gate.py` — main orchestration module. Public API: `run_gate(corpus_root: Path, *, fpr_threshold: float = 0.02, tpr_threshold: float = 0.80) -> FprGateReport`. Internally: iterates corpus via `iter_corpus`; for each fixture, cache-lookup → on miss, invokes the analysis-core pipeline directly (NOT `cleanmatch audit-game` subprocess, to avoid CLI overhead); computes FPR/TPR + 95% CIs; returns a pydantic `FprGateReport` model matching the JSON shape in `contracts/fpr_gate.contract.md`.
- [X] T018 [US3, depends on T017] Create `tests/fixtures/corpora/test_fpr_gate.py` — the actual pytest test target invoked by CI. Single test `test_fpr_gate_passes()`. Calls `run_gate(Path("tests/fixtures/corpora"))`; writes the report to `tests/fixtures/corpora/fpr_gate_report.json`; asserts `report.passed is True`. On failure, the assertion message embeds the diagnostic text from `contracts/fpr_gate.contract.md` §"Output (on failure)". Test is marked `@pytest.mark.fpr_gate` so CI can select it via `pytest -m fpr_gate`.
- [ ] T019 [US3] Source ≥ 50 clean-corpus PGNs per research.md R4. Place under `tests/fixtures/corpora/clean/<descriptive-name>.pgn`. Naming convention: `<year>-<event-or-source>-<round-or-game>.pgn`. Mix: ~30 OTB tournament broadcast games, ~15 streamed top-player games, ~5 pre-2010 GM games. Do NOT commit games whose source URL is not publicly accessible.
- [ ] T020 [US3, depends on T019] For each PGN added in T019, write the sibling `.provenance.json` per FR-005 + `contracts/provenance.schema.json`. `label = "clean"`. `label_confidence` = `"high"` for OTB / streamed games, `"medium"` for pre-2010 archive games. `notes` field captures the specific event/stream/archive context. **Link-rot policy (F8)**: the `source` URL records retrieval-time accessibility; if the URL later 404s, the in-tree PGN remains the source of truth and the fixture is NOT removed — provenance documents the URL state at retrieval, not at audit time.
- [ ] T021 [US3] Source ≥ 20 engine-assisted PGNs per research.md R3 from Lichess closed/flagged accounts. Place under `tests/fixtures/corpora/engine_assisted/<lichess-account-or-game-id>.pgn`. Only use games of publicly-closed accounts (Lichess profile shows `closed: true` with a public reason). After landing the first fixture, `rm tests/fixtures/corpora/engine_assisted/.gitkeep`.
- [ ] T022 [US3, depends on T021] For each engine-assisted PGN added in T021, write the sibling `.provenance.json`. `label = "engine_assisted"`. `label_confidence = "high"` (Lichess system-confirmed). `notes` field MUST acknowledge the Lichess-classifier circularity risk per FR-005 + spec.md Edge Case "Engine-assisted corpus — circularity risk". Example sentence: `"Source: Lichess flagged-account game; label confidence reflects Lichess's classifier — see spec.md circularity edge case."`. Link-rot policy (F8) same as T020: in-tree PGN is source of truth; subsequent URL 404s do not require fixture removal.
- [ ] T023 [US3, depends on T018, T020, T022] Run the gate locally: `uv run pytest tests/fixtures/corpora/test_fpr_gate.py -v`. Expect cold-cache runtime up to 30 min (SC-005). On first pass, gate may fail — if so, document the result in scratch notes BUT do NOT relax thresholds (FR-010 forbids algorithm changes here). Per spec, gate failure → Phase 3 algorithm tuning, not Phase 2 threshold relaxation.
- [X] T024 [US3, depends on T023] Modify `.github/workflows/ci.yml`: add a new `fpr_gate` job that runs after the standard `test` job. Uses `actions/cache@v4` with cache key derived from `engine_binary_sha256 + opening_book_sha256 + hashFiles('tests/fixtures/corpora/**/*.pgn')` per research.md R5. Cache path: `tests/fixtures/corpora/.cache/`. Job invokes `uv run pytest tests/fixtures/corpora/test_fpr_gate.py -v -m fpr_gate`. Uses a `paths:` filter on the workflow trigger so the job only **executes** on PRs touching `packages/heuristics/`, `packages/analysis-core/`, `packages/shared-types/`, or `tests/fixtures/corpora/`. Job uploads `fpr_gate_report.json` as a workflow artifact for diagnostic review. **Note (F5)**: enforcing the job as "required for merge" is a branch-protection setting on `main` configured by the repo maintainer in GitHub UI/API — this task only delivers the workflow; the maintainer step is documented as a one-line note at the bottom of the PR description for this feature.
- [ ] T025 [US3, depends on T024] Verify the CI gate fails-loud on regression: create a throwaway local branch with a one-line change in `packages/heuristics/src/heuristics/scoring/aggregator.py` that adds `+ 0.3` to the final score; push as a draft PR; confirm the `fpr_gate` job fails with the diagnostic text from `contracts/fpr_gate.contract.md`. Delete the draft PR after verification. Document the verified diagnostic format in the PR description of the main Phase 2 PR for SC-006 sign-off.

**Checkpoint**: US3 functional; corpus shipped; gate enforced in CI.

---

## Phase 6: User Story 4 - Reproducibility Manifest Schema Reachability (Priority: P2)

**Goal**: Make the existing `ReproducibilityManifest` reachable in-band on `AuditRun.manifest`. Per research.md R8, the schema fields already exist; the only gap is attaching the persisted manifest to the AuditRun model.

**Independent Test**: `cleanmatch audit-game ... --output json | jq '.manifest.rating_baselines_sha256'` returns a non-zero 64-char hex string (not `null`, not `"0000...0000"`).

### Tests for User Story 4

- [X] T026 [P] [US4] Write `packages/shared-types/tests/test_audit_run_manifest_field.py` — unit tests for the new optional field: (a) `AuditRun(...)` constructed without `manifest=` keeps it as `None`; (b) `AuditRun(..., manifest=<real manifest>)` round-trips through `model_dump_json` / `model_validate_json` byte-identical; (c) extra-forbid still rejects unknown keys (no schema drift).
- [X] T027 [P] [US4] Write `packages/analysis-core/tests/test_run_manifest_attachment.py` — integration test that runs the pipeline against the smoke-test PGN with a stub engine and asserts the returned `AuditRun` has a non-None `manifest` whose `rating_baselines_sha256` and `signal_versions` reflect the bundled artifacts (not the `"0" * 64` / empty-dict defaults).

### Implementation for User Story 4

- [X] T028 [US4] Modify `packages/shared-types/src/shared_types/audit_run.py`: add `manifest: ReproducibilityManifest | None = None` to `AuditRun` per data-model.md §1. Import `ReproducibilityManifest` from `shared_types.report` at top of file. Update the class docstring to mention the new field.
- [X] T029 [US4, depends on T028] Modify `packages/analysis-core/src/analysis_core/pipeline/run.py`: in `_build_run` (and the username-batch builder if it exists), pass `manifest=manifest` to the `AuditRun(...)` constructor. The variable is already computed at lines ~321-335; just thread it through.
- [ ] T030 [US4, depends on T029] Verify end-to-end: `uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json | jq '.manifest.rating_baselines_sha256, .manifest.signal_versions["acpl-analysis"]'`. Both values MUST be non-null and match the expected formats (64-char hex, semver). Document the verified output in the PR description. **Determinism check (closes F2 / SC-007)**: run the same audit a second time into a separate file; assert `jq '.manifest.rating_baselines_sha256, .manifest.opening_book_sha256, .manifest.signal_versions'` is **byte-identical** between the two runs (use `diff <(jq -S '.manifest' run1.json) <(jq -S '.manifest' run2.json)` — empty diff is required). Embed both run sha256s in the PR description.

**Checkpoint**: US4 functional; manifest reachable in-band; all SCs for US4 verifiable from a single CLI invocation.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CHANGELOG, manual smoke, sign-off.

- [X] T031 [P] Modify `CHANGELOG.md` at repo root: extend the `## [2.0.0]` entry per FR-007 + FR-009: record real baselines source ("Lichess Standard 2026-04" + sha256), real book source (URL + sha256), measured FPR + TPR from T023's run (point estimates + 95% CIs), FPR threshold 2.0% (target ≤ 1.5%), TPR threshold 80.0%, sample deltas from T010 (e.g., "smoke-test score: pre=0.464 → post=0.X (Δ ±Y)"). Note the v2.0.0-rc1 → v2.0.0 transition: `AuditRun.manifest` now reachable in-band; rc1 JSONs without it remain readable (None default).
- [X] T032 [P] Modify `packages/heuristics/CHANGELOG.md`: single entry — "rating_baselines.json regenerated from Lichess 2026-04 (real data, sample_size ≥ 1000 per bucket)". No signal version bumps (FR-010).
- [X] T033 [P] Modify `packages/analysis-core/CHANGELOG.md`: entries — "opening_book.bin replaced with real gm2600.bin (sha256 + size)"; "AuditRun.manifest field attached in-band via _build_run".
- [X] T034 [P] Modify `packages/shared-types/CHANGELOG.md`: entry — "AuditRun.manifest optional field added; backward-compatible (defaults None)".
- [X] T035 Run `uv run ruff check . && uv run ruff format --check .` from repo root; fix any violations introduced by Phase 2.
- [X] T036 Run `uv run mypy --strict packages/heuristics/src packages/analysis-core/src packages/shared-types/src`; fix any new type errors. No new `# type: ignore` without inline justification (constitution Principle I).
- [X] T037 Run `uv run pytest --cov=packages --cov-report=term --cov-fail-under=85`; confirm coverage holds at ≥ 85% line / ≥ 80% branch including the new modules (`_provenance_loader.py`, `_engine_cache.py`, `_fpr_gate.py`).
- [ ] T038 Execute `specs/005-scoring-v2-phase2/quickstart.md` end-to-end manually on a fresh checkout; confirm every numbered recipe (US1 refresh, US2 refresh, US3 add-fixture, US3 run-gate, US4 verify-envelope) succeeds. Document any deviation in the PR description.
- [X] T039 Final review against constitution: Principle I (no bloat, lint/type clean), Principle II (tests for every new module — confirm coverage), Principle III (CLI surface unchanged, JSON additive only), Principle IV (FPR-gate warm budget ≤ 5 min verified by CI run-time). Sign off in PR description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. T005 + T006 unblock the FPR-gate work in Phase 5; T003 unblocks T005.
- **User Story phases (3-6)**: All depend on Foundational. US1 and US2 are entirely independent; US3 depends on Foundational (T005/T006) and the real artifacts (US1+US2 should land before T023 runs the gate, or the gate runs against stubs and will be re-validated post-merge); US4 is independent of US1/US2/US3.
- **Polish (Phase 7)**: Depends on US1, US2, US3 (for CHANGELOG content) and US4 (for manifest verification text).

### User Story Dependencies

- **US1 (P1)** depends on Foundational only. Independently testable.
- **US2 (P1)** depends on Foundational only. Independently testable.
- **US3 (P1)** depends on Foundational (T005, T006). The FPR-gate test run (T023) WILL produce meaningful FPR/TPR only after US1 (real baselines) and US2 (real book) have landed, because the algorithm's scoring uses these artifacts. Sequence: US1 + US2 in parallel → US3 corpus assembly + gate code in parallel → T023 (run gate) AFTER US1+US2 + T020/T022 complete.
- **US4 (P2)** depends on Foundational only. Independently testable; can land before, during, or after US3.

### Within Each User Story

- US1: T007 → T008 → T009 (verify) ∥ T010 (delta capture).
- US2: T011 → T012 → T013.
- US3: tests (T014, T015) ∥ utilities (T005, T016) → gate orchestration (T017) → test target (T018); corpus assembly (T019/T020, T021/T022) parallel to code; gate run (T023) gate code AND corpus done; CI wire (T024) → regression smoke (T025).
- US4: tests (T026 ∥ T027) → schema add (T028) → pipeline wire (T029) → e2e verify (T030).

### Parallel Opportunities

- **Within Phase 1**: T001 + T002 parallel.
- **Within Phase 2**: T003 + T004 parallel; T006 parallel with T005 only after T005 is in flight.
- **Across stories**: US1, US2, US4 fully parallel after Phase 2. US3 corpus tasks (T019, T021) parallel with code tasks (T014–T018). Most P-marked tasks within a phase parallel by default.

---

## Parallel Example: P1 stories simultaneous

```bash
# After Phase 2 completes, three developers can run US1, US2, US4 in parallel:

# Developer A — US1 (Lichess baselines refresh):
T007 → T008 → T009 ∥ T010

# Developer B — US2 (gm2600.bin refresh):
T011 → T012 → T013

# Developer C — US4 (AuditRun.manifest field):
T026 ∥ T027 → T028 → T029 → T030

# Developer D — US3 corpus assembly (independent of code work):
T019 → T020   |   T021 → T022

# Developer E — US3 gate code (independent of corpus assembly):
T014 ∥ T015 ∥ T016 → T017 → T018

# Once all the above complete:
T023 (run gate on real corpus + real artifacts) → T024 (CI wire) → T025 (regression smoke)
```

---

## Implementation Strategy

### MVP First (US1, US2, US3 — all P1)

1. Complete Phase 1 (Setup).
2. Complete Phase 2 (Foundational).
3. Complete Phase 3 (US1 — real baselines).
4. Complete Phase 4 (US2 — real book).
5. Complete Phase 5 (US3 — FPR gate). **This is the validation moment**: if gate fails on shipped corpus, the v2.0.0 release is NOT promotable; algorithm tuning becomes the Phase 3 priority. If gate passes, v2.0.0 promotes from `-rc1` to stable.
6. Polish (Phase 7).

### Incremental Delivery (US4 as follow-up PR)

US4 is P2 and ships as a separate small PR for clean reviewability:

- PR 1 (this MVP): US1 + US2 + US3 + Polish.
- PR 2: US4 (AuditRun.manifest field) — small, focused, low risk.

### Parallel Team Strategy

Phase 1 + Phase 2 done by one developer (foundational). Then:

- Developer A: US1 (Lichess refresh — long-running download/script).
- Developer B: US2 (gm2600.bin refresh — short).
- Developer C: US3 gate code (T014–T018).
- Developer D: US3 corpus assembly (T019–T022 — manual research work).
- Developer E: US4 manifest field (T026–T030).
- After all parallel work lands: T023 + T024 + T025 (gate run, CI wire, regression smoke) by one developer.

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story is independently completable and testable post-Phase 2.
- FR-010 forbids any signal algorithm change in Phase 2. Tasks that touch `packages/heuristics/src/` or `packages/analysis-core/src/analysis_core/` are limited to artifact loading, manifest attachment, and CI infrastructure — never scoring math.
- Verify each test fails before implementing (constitution Principle II: red → green → refactor).
- Commit after each task or logical group; use Spec Kit commit prefix.
- Stop at the post-T023 checkpoint to validate the FPR gate on real data before proceeding to T024.
- Avoid: vague tasks; cross-file conflicts on `aggregator.py` or other shared scoring code (this phase touches only `pipeline/run.py` once at T029 for the manifest attachment); corpus fixtures whose source URL is not publicly accessible.
