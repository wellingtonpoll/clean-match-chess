# Feature Specification: Fraud Detection Algorithm v2 — Phase 2: Empirical Validation & Production Artifacts

**Feature Branch**: `005-scoring-v2-phase2`

**Created**: 2026-05-24

**Status**: Draft

**Input**: User description: "Phase 2 closes the four deferred items from `specs/004-scoring-v2-phase1/tasks.md` so the v2.0.0 scoring pipeline ships with verified production artifacts and empirical false-positive-rate (FPR) validation: (1) refresh `rating_baselines.json` from a real Lichess month-export, (2) replace the stub `opening_book.bin` with the verified `gm2600.bin`, (3) extend `ReproducibilityManifest` to persist `rating_baselines_sha256` and `signal_versions`, (4) add a labeled-corpus FPR gate (SC-001/SC-002 from Phase 1)."

## Context

Phase 1 (feature 004) shipped the v2 scoring pipeline with stub data artifacts and without empirical validation, accepted explicitly as a phased delivery. Four follow-ups were documented in `specs/004-scoring-v2-phase1/tasks.md`:

- **T007 fallback**: `packages/heuristics/data/rating_baselines.json` is hand-curated stub (`source_dataset: "hand-curated-stub (Phase 1 fallback; lit. values, not measured)"`). Scoring deltas between rating buckets are literature-based, not measured.
- **T003 stub**: `packages/analysis-core/data/opening_book.bin` is 1.3 KB (real `gm2600.bin` is ~MB). The book exclusion path (`OpeningBook.contains`) returns False for almost all real openings, so engine-correlation samples include book moves that should be excluded.
- **T010 partial**: `_build_run` computes `rating_baselines_sha256` and `signal_versions` but they are dropped because `ReproducibilityManifest` is `frozen + extra="forbid"`. Audit reproducibility is incomplete.
- **SC-001 / SC-002 deferred**: Phase 1 SC-001 (false-positive rate against a clean labeled corpus ≤ target) and SC-002 (true-positive rate against an engine-assisted corpus ≥ target) were demoted to Phase 2 (H3 resolution). No labeled corpus exists in the repo; CI has no FPR gate.

Phase 2 closes all four. Until it ships, v2.0.0 cannot be promoted from `-rc1` to a recommended release for external maintainers.

## Clarifications

### Session 2026-05-24

- Q: Qual false-positive-rate threshold máximo para gate de CI bloquear merge no corpus limpo? → A: **2.0%** (alvo medido ≤ 1.5%, cushion 0.5% absorve drift BLAS/LAPACK entre runners; alinhado com Phase 1 CUSUM convention).
- Q: Qual true-positive-rate mínimo no corpus engine-assisted para CI gate passar? → A: **80.0%** (industry-aligned; tolera casos ambíguos de cheat leve sem afrouxar excessivamente).
- Q: Como obter o corpus engine-assisted (≥ 20 jogos com cheat publicamente disclosado)? → A: **Lichess flagged-account dumps**. Volume alto, label confidence alta (banida pelo sistema). Risco de circularidade com algoritmo Lichess deve ser documentado em provenance.
- Q: Qual Lichess month-export usar para `rating_baselines.json`? → A: **Pin month específico — 2026-04** (último completo antes da release). Reprodutível exato; refresh em release minor futura.
- Q: Qual schema mínimo de `.provenance.json` sibling de cada PGN no corpus? → A: **5 campos: `source`, `retrieved_at`, `label`, `label_confidence`, `notes`** (rastreabilidade temporal + nuance de confidence).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Production Rating Baselines from Real Lichess Data (Priority: P1)

A maintainer regenerates `rating_baselines.json` from a current Lichess month-export so scoring contributions from `acpl-analysis` and rating-bucket-calibrated `engine-correlation` reflect measured population statistics, not literature placeholders.

**Why this priority**: The two highest-weight signals in the v2 aggregator (`acpl-analysis` weight 0.30, `engine-correlation` weight 0.05 + ratio normalization) consume per-bucket expected values directly from this JSON. Wrong baselines = miscalibrated scores at every audit. Blocks v2.0.0 release confidence.

**Independent Test**: After regenerating, re-run the smoke-test PGN (`tests/fixtures/audit_v2_smoke.pgn`) audit. The `acpl-analysis` and `engine-correlation` `weighted_mean` values shift relative to the stub baseline. Document the deltas; assert bucket coverage (all 7 buckets including `rating-unknown`) and minimum sample-size per bucket meet the documented threshold.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** maintainer runs `build_baselines.py` against a real Lichess month-export, **Then** the resulting JSON's `source_dataset` field references the dataset (URL + date) and every bucket has `sample_size ≥ 1000`.
2. **Given** the new baselines committed, **When** the smoke-test audit runs, **Then** `manifest.rating_baselines_sha256` differs from the Phase 1 stub sha256, and the H1 sample deltas (per T042b convention) are documented in `CHANGELOG.md`.
3. **Given** a freshly built JSON, **When** the schema validator in `rating_baselines/__init__.py` loads it, **Then** validation passes (no schema drift introduced by real data).

---

### User Story 2 - Production Opening Book Verified Against Upstream (Priority: P1)

A maintainer downloads the canonical `gm2600.bin` polyglot opening book, verifies its sha256 against the upstream source documented in `research.md`, and commits it as `packages/analysis-core/data/opening_book.bin`.

**Why this priority**: Phase 1's stub book has near-zero coverage. `is_book = True` flag is almost never set, so engine-correlation samples include the first ~12 plies of every game where moves are book-following, not player choice. Inflates false-positive rate. Blocks SC-001 work in US3.

**Independent Test**: Audit the Italian Game smoke-test PGN twice — once with the new book, once with an empty stub. Assert `samples` count for `engine-correlation` differs by ≥ 10 plies (matching US4 AS1 from Phase 1). With the new book, the first 12 plies of standard openings (Italian, Sicilian, Ruy Lopez) have `is_book = True`.

**Acceptance Scenarios**:

1. **Given** a clean checkout, **When** maintainer downloads `gm2600.bin` from the canonical source and replaces the stub, **Then** the new file's sha256 matches the upstream value recorded in `packages/analysis-core/data/README.md`, and file size is ≥ 1 MB.
2. **Given** the new book committed, **When** the smoke-test audit runs, **Then** the first 12 plies of a standard opening are flagged `is_book = True` and excluded from the engine-correlation sample denominator.
3. **Given** the book sha256 changes, **When** any audit runs, **Then** `manifest.opening_book_sha256` reflects the new value (already wired by Phase 1 T010).

---

### User Story 3 - False-Positive-Rate Gate Against Labeled Corpus (Priority: P1)

A maintainer (or CI) runs the v2 pipeline against a labeled corpus of clean games (titled-player streams, public broadcasts, OTB tournament games) and an engine-assisted corpus (publicly disclosed cheat cases, Lichess-flagged accounts) and the system blocks merges if false-positive rate exceeds the documented threshold.

**Why this priority**: This is the empirical validation that the algorithm actually works. Without it, v2.0.0's correctness claims are unverified. Phase 1 explicitly deferred SC-001 and SC-002 here. Blocks promotion of v2.0.0 to a stable release for downstream consumers.

**Independent Test**: Run the full audit pipeline against the labeled corpus. Assert: (a) clean corpus FPR ≤ documented threshold (e.g., 2%); (b) engine-assisted corpus TPR ≥ documented threshold (e.g., 80%); (c) the CI gate fails a synthetic PR that intentionally regresses the algorithm (e.g., flips a sign in `aggregator.py`).

**Acceptance Scenarios**:

1. **Given** a labeled corpus committed under `tests/fixtures/corpora/{clean,engine_assisted}/`, **When** the FPR-gate test runs, **Then** it computes per-corpus aggregate score distribution and asserts FPR/TPR against documented thresholds.
2. **Given** a regression PR that intentionally biases scores high on the clean corpus, **When** CI runs, **Then** the FPR-gate job fails and blocks merge with a clear diagnostic ("FPR 4.2% exceeds threshold 2.0% on clean corpus; offending fixtures: …").
3. **Given** a normal PR that does not affect scoring, **When** CI runs, **Then** the FPR-gate job passes in under the CI time budget (target ≤ 5 minutes on standard runners) by caching engine analyses against fixture sha256.

---

### User Story 4 - Reproducibility Manifest Schema Extension (Priority: P2)

A consumer of audit JSON output (CLI, frontend, downstream tools) sees `rating_baselines_sha256` and `signal_versions` in `manifest`, enabling them to reproduce an audit bit-exactly given the same inputs and pinned versions.

**Why this priority**: Reproducibility is constitutional (Principle V) but the missing fields don't break scoring — they only affect downstream provenance tooling. Lower priority than artifact corrections and FPR gate.

**Independent Test**: Run any audit; assert `manifest.rating_baselines_sha256` and `manifest.signal_versions` are present, non-empty, and match the values computed in `_build_run`.

**Acceptance Scenarios**:

1. **Given** the extended `ReproducibilityManifest` schema, **When** an audit JSON is exported, **Then** `manifest.rating_baselines_sha256` is a 64-char hex string and `manifest.signal_versions` is a dict mapping signal names to version strings (e.g., `{"acpl-analysis": "1.0.0", "engine-correlation": "2.0.0", ...}`).
2. **Given** the schema change, **When** existing audit JSONs from v2.0.0-rc1 are loaded, **Then** they either fail loudly (caller must regenerate) or load with the new fields defaulted — behavior is documented and consistent.
3. **Given** two audits run with identical inputs and same baselines/book, **When** their manifests are compared, **Then** `rating_baselines_sha256`, `opening_book_sha256`, and `signal_versions` are byte-identical.

---

### Edge Cases

- **Baselines refresh — dataset unavailable**: If Lichess month-export is down or quota-blocked, the maintainer should be able to skip US1 in this branch and fall back to the stub (Phase 1 behavior), but the CHANGELOG must clearly state which baseline is shipped. The script should also support a `--dry-run` (already implemented in T004) and a clear error mode for partial downloads.
- **Book download — sha256 mismatch**: If the downloaded `gm2600.bin` doesn't match the upstream-documented sha256, the task must fail loudly and not silently commit a tampered or corrupted file. No fallback.
- **Corpus — labeling errors**: A "clean" corpus game later revealed to be cheat-assisted contaminates the FPR measurement. Mitigation: source from extreme-high-trust contexts (OTB tournament broadcasts, top-100 player streams) and document each fixture's provenance.
- **FPR gate — threshold flakiness**: If FPR is measured at 1.8% with a 2.0% threshold, BLAS/LAPACK drift across CI runners could flip it. Mitigation: cushion (target ≤ 1.5% with gate at 2.0%) and seed every RNG.
- **Manifest schema — backward incompatibility**: External consumers reading v2.0.0-rc1 JSONs may break when the new schema lands. Mitigation: ship as v2.0.0 (the first stable release) so no consumer has yet relied on the rc1 schema; document in CHANGELOG.
- **Engine-assisted corpus — circularity risk**: Lichess flagged-account games are labeled by Lichess's own classifier (possibly similar in spirit to our v2 algorithm). Risk: high TPR could reflect shared blind spots, not true detection. Mitigation: each engine-assisted fixture's `.provenance.json` `notes` field MUST acknowledge this; Phase 3 backlog tracks adding non-Lichess-sourced cases (federation bans + admissions) as cross-validation when feasible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST ship `rating_baselines.json` whose `source_dataset` field references the **Lichess Standard month-export for 2026-04** (URL + retrieval date), with per-bucket `sample_size ≥ 1000` for all 6 rating buckets and the `rating-unknown` bucket. If 2026-04 is unavailable at execution time, fall back to the most recent prior complete month (2026-03 or earlier) and document the substitution in `source_dataset`.
- **FR-002**: System MUST ship `opening_book.bin` whose sha256 matches the upstream-documented value recorded in `packages/analysis-core/data/README.md`, with file size ≥ 1 MB.
- **FR-003**: System MUST expose `ReproducibilityManifest` provenance in-band on the `AuditRun` returned to callers. The schema fields (`rating_baselines_sha256: str`, `signal_versions: dict[str, str]`) already exist on `ReproducibilityManifest` per Phase 1 — Phase 2 closes the gap by attaching the persisted manifest to `AuditRun.manifest` so JSON envelopes carry the provenance without requiring a separate disk read. (Research R8 documents the Phase 1 T010 status reconciliation.)
- **FR-004**: System MUST persist `rating_baselines_sha256` and `signal_versions` in every audit's manifest (i.e., remove the "computed but dropped" partial from Phase 1 T010).
- **FR-005**: System MUST include a labeled corpus under `tests/fixtures/corpora/clean/` with ≥ 50 verified-clean games (sourced from OTB tournament broadcasts and top-titled player streams) and `tests/fixtures/corpora/engine_assisted/` with ≥ 20 games drawn from **Lichess flagged-account dumps** (accounts banned by Lichess for engine assistance). Each fixture file MUST have a sibling `.provenance.json` with exactly these fields: `source` (URL or canonical identifier), `retrieved_at` (ISO-8601 UTC), `label` (`"clean"` or `"engine_assisted"`), `label_confidence` (`"high"` / `"medium"` / `"low"`), `notes` (free-form caveats — for engine-assisted Lichess fixtures, MUST acknowledge potential circularity with Lichess's own classifier).
- **FR-006**: System MUST provide a CI job (or test target) that audits every fixture in `tests/fixtures/corpora/` and computes aggregate FPR (clean corpus) and TPR (engine-assisted corpus). The job MUST fail if FPR exceeds the documented threshold or TPR falls below the documented threshold.
- **FR-007**: System MUST document the FPR threshold (**2.0%**, with internal target ≤ 1.5%) and TPR threshold (**80.0%**) in `CHANGELOG.md` v2.0.0 entry. (Rationale already captured in this file's Clarifications section and SC-003.)
- **FR-008**: System MUST cache engine analyses by fixture sha256 so the FPR-gate CI job completes within a 5-minute wall budget on a standard GitHub runner (per Principle IV — performance budgets).
- **FR-009**: System MUST update `CHANGELOG.md` v2.0.0 entry to record: real baselines source + sha256, real book source + sha256, measured FPR + TPR on shipped corpus, signal_versions persisted.
- **FR-010**: System MUST NOT change any signal version (`acpl-analysis`, `engine-correlation`, `regime-shift`, `timing-analysis`, `blunder-suppression`) — Phase 2 is artifact + validation work only. Algorithm changes belong in Phase 3.

### Key Entities

- **Rating Baselines Artifact** (`packages/heuristics/data/rating_baselines.json`): JSON conforming to `contracts/rating_baselines.schema.json`. Per-bucket expected values for ACPL mean, ACPL stdev, top-1 match rate, weighted-top-1 match rate, and optionally top-3 match rate. Provenance fields: `source_dataset`, `generated_at`, `version`.
- **Opening Book Artifact** (`packages/analysis-core/data/opening_book.bin`): Polyglot binary opening book (gm2600.bin family). Documented upstream sha256 + retrieval date in sibling `README.md`.
- **Reproducibility Manifest** (`packages/shared-types/src/shared_types/...`): Frozen dataclass embedded in every `AuditRun`. Extended fields: `rating_baselines_sha256`, `signal_versions`.
- **Labeled Corpus** (`tests/fixtures/corpora/`): Two subdirectories — `clean/` (verified-clean games from OTB broadcasts + top-titled streams) and `engine_assisted/` (games from Lichess-flagged accounts). Each PGN has a sibling `.provenance.json` with the 5 fields fixed by FR-005.
- **FPR-Gate CI Job**: Test target invoked by CI that audits every corpus fixture, computes aggregate score distribution, and asserts FPR/TPR against documented thresholds.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The shipped `rating_baselines.json` references a real public dataset; per-bucket sample size ≥ 1000; smoke-test audit scores shift measurably (documented in CHANGELOG) from Phase 1 stub baseline.
- **SC-002**: The shipped `opening_book.bin` matches its upstream-documented sha256; the Italian Game smoke-test PGN flags ≥ 12 plies as `is_book = True`.
- **SC-003**: False-positive rate on the clean labeled corpus is ≤ 2.0% (target ≤ 1.5% with 0.5% cushion) at the recommended scoring threshold; true-positive rate on the engine-assisted corpus is ≥ 80.0% at the same threshold.
- **SC-004**: Every audit JSON produced by the v2.0.0 pipeline includes a non-empty `rating_baselines_sha256` and `signal_versions` in `manifest`.
- **SC-005**: The FPR-gate CI job completes in ≤ 5 minutes on a standard GitHub runner with cached engine analyses; cold-cache run completes in ≤ 30 minutes.
- **SC-006**: A deliberately algorithm-regressing PR (e.g., one that biases all clean-corpus scores up by 0.3) is blocked by CI with a clear diagnostic that names the threshold breach and at least one offending fixture.
- **SC-007**: Re-running an audit on identical inputs produces byte-identical `manifest.rating_baselines_sha256`, `manifest.opening_book_sha256`, and `manifest.signal_versions`.

## Assumptions

- Lichess month-export remains publicly available and rate-limited only to a level compatible with a one-shot maintainer download (assumption inherited from Phase 1 research.md R2).
- A canonical `gm2600.bin` source documented in Phase 1 research.md R1 is reachable; if the upstream URL rots, the task includes recording the new source URL alongside its sha256.
- Engine-assisted corpus games are sourceable from publicly disclosed cases (federation bans, admissions, Lichess account closures with public announcements). No private or leaked data is used.
- Clean corpus games are sourceable from OTB tournament broadcasts, top-titled player streams (with permissive licensing), and similar high-trust contexts.
- CI runners can execute engine analyses with cached results keyed by fixture sha256; cache is shared across CI jobs (e.g., via GitHub Actions cache or a similar mechanism).
- The FPR threshold (2.0%, target ≤ 1.5%) and TPR threshold (80.0%) are **confirmed** via Clarifications session 2026-05-24, aligned with the Phase 1 CUSUM false-positive cushion convention (1.5% target, 0.5% cushion).
- Phase 2 does NOT change signal algorithms; it only ships real artifacts and adds validation. Any FPR breach revealed by the gate is fixed in Phase 3 (algorithm tuning), not Phase 2.
- `ReproducibilityManifest` schema extension is acceptable as a non-additive breaking change in v2.0.0 (vs rc1) because no external consumer relies on rc1 manifest schema yet.
- Backward-compatibility with v2.0.0-rc1 audit JSONs is NOT a requirement; consumers regenerate audits if they need the new schema.
