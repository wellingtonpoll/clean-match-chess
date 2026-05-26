# Feature Specification: Scoring v2 Phase 2 Completion

**Feature Branch**: `007-scoring-v2-phase2-completion`

**Created**: 2026-05-25

**Status**: Draft

**Input**: User description: "Planejamento das implementações que vão utilizar o dump `lichess_db_standard_rated_2026-04.pgn.zst` baixado localmente — fechar todas as pendências deferidas do feature 005 (baselines reais, corpus engine-assisted, FPR-gate run, score deltas) via spec-kit."

## Context

Feature 005 (Scoring v2 Phase 2) merged at commit `784729f` with four explicit deferrals documented in `CHANGELOG.md:139-153` under `### Pending (Feature 005 — to land before v2.0.0 promotion)`. The maintainer has now downloaded `lichess_db_standard_rated_2026-04.pgn.zst` (28 GB compressed, ~170 GB decompressed) to the repo root, which unblocks deferral #1. This spec closes all four deferrals.

The current scoring pipeline calibrates two signals (`acpl-analysis`, `engine-correlation/weighted`) against **literature-derived guesses** (Regan 2011 + Lichess insights aggregates) with `sample_size=100` placeholders per bucket. Players are judged against an *estimated* human-population baseline rather than a *measured* one. This feature closes that gap: every bucket in `packages/heuristics/data/rating_baselines.json` will be backed by ≥5000 measured games at Stockfish-16 depth 12.

## Clarifications

### Session 2026-05-25 (pre-plan)

- **Q**: Should the scope cover only baselines (T007-T010 + `build_buckets_real` implementation), or all deferred 005 work? **A**: All deferred 005 work — close the pending stanza entirely.
- **Q**: Should the Lichess month be the spec-pinned 2025-06, or the 2026-04 already on disk? **A**: 2026-04 + documented deviation. Provenance preserved by sha256 of the archive, not by month string.
- **Q**: Sample size per bucket — 5000 (6 h CPU), 3000 (3.5 h), or 1500 (1.5 h)? **A**: 5000. FR-001 requires n ≥ 1000; 5× headroom stabilises ACPL stdev (the most variance-sensitive output).
- **Q**: SemVer policy on the resulting CHANGELOG entry? **A**: Bump to `2.1.0` (minor). Measured scores will move materially vs the stub on identical inputs; consumers will notice.
- **Q**: PR strategy — single or split? **A**: Single PR. FPR-gate validation (T013) cannot run until both real baselines AND engine-assisted corpus exist together, so splitting does not parallelise the critical path.

## User Scenarios & Testing *(mandatory)*

### User Story A — Real measured baselines replace the literature stub (Priority: P1)

The maintainer runs `build_baselines.py` against the local Lichess 2026-04 archive. The script streams the archive, filters games to the eligibility window, reservoir-samples 5000 per bucket, runs Stockfish depth 12 over the 30 000 sampled games, and writes a `rating_baselines.json` with measured per-bucket `expected_top1`, `expected_weighted_top1`, `expected_acpl_mean`, `expected_acpl_stdev`. The output is sha256-stable, schema-valid, and reproducible from the seed + source archive sha256.

**Why this priority**: P1 — every other deferral depends on this. The FPR-gate (USC) cannot be validated meaningfully against a stub baseline, and the score-delta documentation (USD) requires this output to compute the delta.

**Independent Test**: Run the script with `--seed 0` twice on the same archive; resulting JSON files must be byte-identical. Validate against `specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json`. Confirm `sample_size ≥ 1000` for every bucket.

**Acceptance Scenarios**:

1. **Given** the local Lichess 2026-04 archive and SF16 Docker image, **When** the maintainer runs `uv run python packages/heuristics/scripts/build_baselines.py --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst --stockfish-cmd "docker run --rm -i cleanmatch-stockfish:sf16" --seed 0 --per-bucket-sample 5000 --output packages/heuristics/data/rating_baselines.json`, **Then** the resulting JSON is schema-valid, has `sample_size ≥ 1000` in every bucket, and carries `source_dataset = "lichess_db_standard_rated_2026-04 (sha256=<hex>)"`.
2. **Given** the same archive + seed, **When** the script is re-run, **Then** the output JSON is byte-identical to the previous run (sha256 match).
3. **Given** an audit run against `tests/fixtures/audit_v2_smoke.pgn` before and after replacing the baselines, **When** `jq '.manifest.rating_baselines_sha256'` is compared, **Then** the two sha256 values differ, and `score.score` moves by ≥ 0.005 in absolute value (proving measured baselines have observable effect).
4. **Given** the FR-001 floor `n ≥ 1000`, **When** any bucket would yield `< 1000` samples (e.g. the 2401+ bucket on a sparse month), **Then** the script exits non-zero with a clear error naming the deficient bucket and the available count.

---

### User Story B — Engine-assisted corpus (≥20 PGNs) lands under `tests/fixtures/corpora/engine_assisted/` (Priority: P1)

The maintainer sources 25 PGNs (5-fixture buffer above the 20-game floor) from publicly-disclosed Lichess banned-account threads. Each PGN ships with a sibling `.provenance.json` matching `tests/fpr_gate/contracts/provenance.schema.json`, with `label = "engine_assisted"`, `label_confidence = "high"`, and the canonical Lichess-classifier circularity acknowledgement in `notes`.

**Why this priority**: P1 — required for FPR-gate TPR measurement (USC) and SC-001 acceptance.

**Independent Test**: Run `uv run pytest tests/fpr_gate/test_provenance.py -v`; all 25 sibling files validate against the provenance schema. Run `tests/fpr_gate/_corpus_extract.py` to inspect bucket counts.

**Acceptance Scenarios**:

1. **Given** publicly-disclosed banned-account IDs from Lichess forum + r/chess archive, **When** the maintainer runs the API call `https://lichess.org/api/games/user/<id>?max=5&tags=true` per disclosed ID, **Then** the resulting PGNs are committed to `tests/fixtures/corpora/engine_assisted/<lichess-id>.pgn`.
2. **Given** each committed PGN, **When** the sibling `.provenance.json` is created, **Then** it validates against `provenance.schema.json`, `label = "engine_assisted"`, `label_confidence = "high"`, and `notes` contains the exact sentence: *"Lichess flagged-account game; label confidence reflects Lichess's own classifier — see spec.md FR-005 circularity edge case."*
3. **Given** ≥ 20 fixtures present, **When** the FPR-gate runs in cold-cache mode, **Then** the TPR diagnostic from `fpr_gate.contract.md §Output` reports an `n` matching the corpus size and a `tpr` value ≥ 80.0% with a 95% confidence interval whose lower bound is non-null.

---

### User Story C — Full FPR-gate validation (T013 + T014 + T015) (Priority: P1)

With real baselines + engine-assisted corpus in place, the maintainer runs the full FPR-gate, verifies it would catch a regression, and confirms determinism via two consecutive audits.

**Why this priority**: P1 — closes 005 acceptance criterion SC-003. Without this run the labelled-corpus FPR claim remains unproven.

**Independent Test**: `uv run pytest tests/fpr_gate/test_fpr_gate.py -v -m fpr_gate --no-cov` returns 0; `tests/fixtures/corpora/fpr_gate_report.json` reports `fpr ≤ 0.02`, `tpr ≥ 0.80`, both 95% CIs non-null.

**Acceptance Scenarios**:

1. **Given** real baselines + ≥ 20 engine-assisted PGNs + the existing 50 clean OTB PGNs, **When** the gate runs in cold-cache mode, **Then** the gate passes with `fpr ≤ 0.02` and `tpr ≥ 0.80`.
2. **Given** a throwaway branch that biases the aggregator score by +0.3, **When** a draft PR is opened against `main` with the `scoring` label, **Then** the CI `fpr_gate` job fails with the diagnostic from `fpr_gate.contract.md §Output`.
3. **Given** the smoke fixture `tests/fixtures/audit_v2_smoke.pgn`, **When** two consecutive `cleanmatch audit-game` runs are performed, **Then** the diff of `jq -S .manifest` between the two JSON outputs is empty (manifest sha256 identical).
4. **Given** a gate run that fails (e.g. FPR > 2%), **When** the maintainer reviews the result, **Then** FR-010 prohibits relaxing the threshold; the failure is escalated as Feature 008 (algorithm tuning), not absorbed in 007.

---

### User Story D — Measured metrics + score deltas documented in CHANGELOG and HANDOFF (Priority: P2)

The maintainer transfers the four bullets from `### Pending (Feature 005 — to land before v2.0.0 promotion)` into the `### Added — Feature 005 (Scoring v2 Phase 2)` block immediately above, substituting measured FPR/TPR/CI/score-delta values for the placeholders. The `[Unreleased]` block becomes `## [2.1.0] — <today>`. A new `packages/heuristics/data/README.md` records source URL, sha256 of the local zst, retrieval date, exact build command, and Stockfish sha256.

**Why this priority**: P2 — the data shift in USA is observable to consumers; the documentation update is required for SemVer + release-notes integrity. Lower than P1 because it cannot start until USA + USC report numbers.

**Independent Test**: `git diff main..HEAD -- CHANGELOG.md` shows the four Pending bullets removed from the Pending stanza and re-inserted into Added with concrete measured values (no `<placeholder>` strings remain). `[2.1.0]` header present with today's date.

**Acceptance Scenarios**:

1. **Given** measured FPR/TPR/CI from USC, **When** the CHANGELOG is edited, **Then** all four Pending-stanza bullets are moved to the Added stanza, the `[Unreleased]` header is replaced with `## [2.1.0] — <today>`, and no `<placeholder>` text remains.
2. **Given** the pre/post audit snapshots from USA, **When** the CHANGELOG entry is written, **Then** it contains both the pre-stub score, the post-real score, and the absolute delta for `tests/fixtures/audit_v2_smoke.pgn`.
3. **Given** the new `rating_baselines.json`, **When** `packages/heuristics/data/README.md` is created, **Then** it records the source URL of the upstream archive, sha256 of the local `.zst`, retrieval date, exact build command + seed, and the Stockfish binary sha256.
4. **Given** the completed work, **When** `specs/005-scoring-v2-phase2/HANDOFF.md` and `specs/005-scoring-v2-phase2/tasks.md` are updated, **Then** T007, T008, T009, T010, T021, T022, T023, T025, T030, T038 are marked `[X]` and the HANDOFF blocks A-2 / B-2 / C / D link to feature 007's PR.

---

### Edge Cases

- **Stream corruption mid-archive**: `chess.pgn.read_game()` returns `None` on EOF; the streaming loop must tolerate truncation and log the byte offset of the last successful game. A `--resume-from CHECKPOINT_DIR` flag allows restart after Phase-1 sampling checkpoints have been written.
- **6-hour build aborts (laptop sleep, OOM)**: Phase-1 checkpoints under `/tmp/baselines-007/*.sample.pgn` enable Phase-2 restart without re-streaming.
- **Engine-assisted account purged before retrieval**: 25-fixture buffer over the 20-game floor; `.provenance.json` cites archive.org snapshot of the original ban announcement.
- **FPR > 2% on real run**: FR-010 prohibits threshold relaxation; failure is escalated as Feature 008.
- **Stockfish nondeterminism**: forced `Threads=1, Hash=256` already enforced in `packages/analysis-core/src/analysis_core/engine/analysis.py:108`; no spec exposure.
- **Lichess classifier circularity (FR-005)**: TPR is bounded by Lichess's own classifier accuracy on the disclosed cases; spec explicitly accepts this circularity in `.provenance.json` notes per acceptance scenario B-2.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `build_baselines.py` MUST sample ≥ 1000 games per bucket; default `--per-bucket-sample = 5000`.
- **FR-002**: Bucketing key MUST be `min(WhiteElo, BlackElo)`; the 7th bucket `rating-unknown` MUST be the element-wise median of the 6 rated buckets.
- **FR-003**: The streaming filter MUST accept games where `600 ≤ WhiteElo ≤ 3500`, `600 ≤ BlackElo ≤ 3500`, time-control category ∈ {RAPID, CLASSICAL}, ply count ≥ 20.
- **FR-004**: Sampling MUST be deterministic for a given seed (`random.Random(seed)`, never module-level `random`). Two runs with `--seed 0` MUST produce byte-identical output JSONs.
- **FR-005**: Engine-assisted fixture `.provenance.json` files MUST contain the canonical circularity-acknowledgement sentence in `notes`, copied verbatim across all 25 fixtures.
- **FR-006**: The FPR-gate MUST pass with `fpr ≤ 0.02` AND `tpr ≥ 0.80` on the real corpus to be considered green.
- **FR-007**: Two consecutive `cleanmatch audit-game` invocations against the same fixture MUST produce manifests with identical sha256.
- **FR-008**: `packages/heuristics/data/README.md` MUST record source URL, local archive sha256, retrieval date, build command + seed, and Stockfish binary sha256.
- **FR-009**: The CHANGELOG `[2.1.0]` block MUST quote measured FPR (with 95% CI), measured TPR (with 95% CI), absolute score delta on the smoke fixture, and the new `rating_baselines.json` sha256.
- **FR-010**: No scoring-algorithm changes — weights, thresholds, signal versions, bootstrap N — are in scope. If the FPR-gate fails, escalate to Feature 008; do NOT relax the gate.

### Key Entities

- **`RatingBaselines`** (existing — `packages/heuristics/src/heuristics/rating_baselines/`): seven-bucket JSON envelope. Schema in `specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json`. No schema changes in this feature.
- **`PGNProvenance`** (existing — `tests/fpr_gate/contracts/provenance.schema.json`): five-field provenance sibling for every corpus PGN. No schema changes.
- **`ReproducibilityManifest`** (existing — `packages/analysis-core/src/analysis_core/manifest.py`): already stamps `rating_baselines_sha256` + `rating_baselines_version`. No schema changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `rating_baselines.json` `sample_size` is ≥ 1000 in every bucket; `source_dataset` matches `"lichess_db_standard_rated_2026-04 (sha256=<hex>)"`.
- **SC-002**: Re-running `build_baselines.py` with the same seed + archive yields byte-identical JSON (sha256 match).
- **SC-003**: FPR-gate cold-cache run reports `fpr ≤ 0.02` and `tpr ≥ 0.80` on the real corpus with non-null 95% CIs.
- **SC-004**: Two consecutive `cleanmatch audit-game` runs against `tests/fixtures/audit_v2_smoke.pgn` produce manifests with identical sha256.
- **SC-005**: `score.score` on `tests/fixtures/audit_v2_smoke.pgn` moves by ≥ 0.005 in absolute value between the stub baseline and the real baseline (proves baselines are observably effective).
- **SC-006**: Regression smoke (throwaway branch with +0.3 score bias) fails the CI `fpr_gate` job with the diagnostic from `fpr_gate.contract.md §Output`.
- **SC-007**: `git diff main..HEAD -- CHANGELOG.md` shows the four Pending-stanza bullets moved to Added with measured numerical values, and a new `## [2.1.0] — <today>` header.

## Assumptions

- The Lichess 2026-04 archive at the repo root is uncorrupted (sha256 verified at build time).
- A Stockfish-16 binary is reachable either via the bundled Docker image or `shutil.which("stockfish")` on the maintainer machine.
- At least 20 publicly-disclosed Lichess banned-account IDs can be sourced before commit (forum threads + r/chess archive are stable enough for retrieval at build time).
- No algorithm tuning is required — measured FPR/TPR meet the gate thresholds on first run. If not, scope escalates to Feature 008 (out of 007).
- The maintainer has ≥ 6 hours of available wall-clock time (or background capacity) for the build pass + ≥ 0.5 day for engine-assisted sourcing.

## Constraints

- Cannot relax `fpr ≤ 0.02` or `tpr ≥ 0.80` per FR-010.
- Cannot modify schemas at `specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json` or `tests/fpr_gate/contracts/provenance.schema.json` (locked by 004 / 005 contracts).
- Cannot use module-level `random` calls — determinism (FR-004 / SC-002) requires `random.Random(seed)` instances only.
- Cannot commit the source archive itself (28 GB > GitHub file limit + `.gitignore`'d at repo root).
- Cannot use chess.com API or any non-Lichess source for the engine-assisted bucket — provenance circularity is bounded to Lichess's own classifier per FR-005.

## Scope notes

- No scoring algorithm changes — explicit FR-010.
- No frontend changes — feature 006 already shipped the web surface that consumes these scores.
- No new CI workflow jobs — existing `fpr_gate` and `test` jobs are reused; only the `scoring` label needs applying when the PR opens.
- No new schema contracts — both `rating_baselines.schema.json` (from 004) and `provenance.schema.json` (from 005) are reused unchanged.
