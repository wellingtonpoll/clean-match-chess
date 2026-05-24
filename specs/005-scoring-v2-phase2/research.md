# Phase 0 Research — Feature 005 (Scoring v2 Phase 2)

**Branch**: `005-scoring-v2-phase2` | **Date**: 2026-05-24

This file resolves the open questions inherited from feature 004's deferrals and the new ones raised by Phase 2's empirical-validation scope. Each block follows the Decision / Rationale / Alternatives format.

---

## R1 — Lichess Month-Export Source for `rating_baselines.json`

**Decision**: Pin the **Lichess Standard Open Database export for 2026-04** at `https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst`. Record the file's sha256 in `rating_baselines.json` under a new `source_dataset_sha256` field (or document it in the `source_dataset` string if schema change is undesirable).

**Rationale**:
- Lichess Open Database is the canonical public source for population-level rating statistics; already referenced in feature 004 research.md R2 as the dataset shape `build_baselines.py` was written against.
- Pinning a specific month (2026-04 = latest complete month before the v2.0.0 release window) makes the artifact reproducible: re-running `build_baselines.py` from the same maintainer machine against the same input produces a byte-identical JSON (modulo a `generated_at` timestamp, already handled by the script).
- 2026-04 contains an estimated 80M+ rated games across all time controls → per-bucket sample sizes well above the FR-001 threshold of 1000 once we restrict to the bucket-relevant rating ranges.

**Alternatives considered**:
- *Latest at-execution-time*: rejected. Non-deterministic; same script run two months apart produces different baselines for the same source URL. Violates SC-007 reproducibility intent.
- *Multi-month aggregation (3-6 months)*: rejected for Phase 2 scope. More robust statistically but multiplies download size (one month is already multi-GB) and complicates provenance. Revisit in a future minor release if seasonal variance is observed.
- *Hand-curated stub (Phase 1 fallback)*: rejected; this is exactly what we're replacing.

**Implementation note**: Lichess publishes the database under CC0 (public domain dedication). No license attribution required; documenting the source URL + retrieval date in `source_dataset` is sufficient.

---

## R2 — `gm2600.bin` Opening Book Provenance

**Decision**: Source `gm2600.bin` from the canonical polyglot-format archive at `https://github.com/michaelb/Sayuri-chess-bot/raw/main/books/gm2600.bin` (or equivalent mirror — record the exact URL used at retrieval time). Expected file size ≈ 1.5 MB. Compute sha256 at download; record in `packages/analysis-core/data/README.md` alongside the URL and retrieval date.

**Rationale**:
- `gm2600.bin` is a well-known polyglot opening book derived from games played by players rated ≥ 2600 Elo. Coverage spans all common openings to ~12-15 plies — exactly the range where the engine-correlation signal would otherwise be contaminated by book-following moves.
- The book is binary-stable: once a sha256 is recorded, identity is verifiable forever. No version drift risk.
- Multiple mirrors exist (chess-engine sources frequently re-host); if one rots, recording the sha256 lets the maintainer find any equivalent copy.

**Alternatives considered**:
- *Other polyglot books (Cerebellum, Goi, etc.)*: rejected for Phase 2. `gm2600.bin` was already chosen in Phase 1 research R1; switching books in Phase 2 would expand scope (require re-tuning book-coverage tests).
- *Generate a fresh book from a high-quality PGN corpus*: rejected. Build-time cost, license complexity for the source PGNs, and no measurable quality gain over `gm2600.bin` at this stage.

**Failure mode**: If the canonical URL is unreachable AND no mirror with a matching sha256 is found, Phase 2 cannot ship its US2 deliverable. Plan tasks include a network-availability check as the first US2 step so this failure surfaces early, not after corpus assembly.

---

## R3 — Engine-Assisted Corpus Sourcing (Lichess Flagged Accounts)

**Decision**: Source the ≥ 20 engine-assisted PGNs from **publicly archived games of Lichess accounts that were closed for engine assistance**. Use the Lichess public ban announcements (forum posts, the `closed for using outside assistance` flag visible on closed account profiles) as the labeling source. Each fixture's `.provenance.json` will record the account URL, the closure-announcement URL (or archived link), and the closure date.

**Rationale**:
- Lichess publishes a `closed: true` flag with a public reason on banned accounts. Their games remain accessible via the public API even after closure. This is the highest-volume, lowest-friction public source for cheat-labeled games.
- Label confidence is high (Lichess's own classifier banned the account) but **not perfect** — there is documented risk of circularity: Lichess may use heuristics similar in spirit to our v2 algorithm, so a high TPR could partly reflect shared blind spots. This is explicitly acknowledged in `spec.md` Edge Cases and each fixture's `.provenance.json` `notes` field per FR-005.
- Legal/ethical: only publicly accessible games of publicly closed accounts are used. No private data, no de-anonymization beyond what Lichess itself publishes.

**Alternatives considered**:
- *FIDE/USCF federation bans + admissions*: higher label confidence (human investigations), but volume is < 20 games realistically attainable in Phase 2 scope. Phase 3 backlog item: add federation-sourced cases as cross-validation.
- *Synthetic engine-played games*: rejected. Distribution doesn't match real cheating patterns (engine assist is sporadic / endgame-only / move-specific in real cases); would inflate TPR artificially.
- *Mix of all three*: rejected for Phase 2 scope. Multiplies provenance work without measurably stronger validation at this stage.

**Cross-validation followup**: Phase 3 should add a small (5-10 game) federation-confirmed sub-corpus to detect any TPR drop relative to the Lichess-only corpus — that drop would quantify the circularity risk.

---

## R4 — Clean Corpus Sourcing

**Decision**: Source the ≥ 50 verified-clean PGNs from three high-trust contexts:
1. **OTB tournament broadcasts** (e.g., Chess.com Tour events, Tata Steel, Candidates) where on-site arbiters confirm fair-play in real time. Use the official PGN downloads from the event websites or `lichess.org/broadcasts`.
2. **Top-100 player Lichess/chess.com accounts** for games played under streamed conditions (camera on, audience visible) — these are effectively continuously audited by viewers.
3. **Pre-2010 archived games** from the ChessBase MegaBase or `https://www.pgnmentor.com/` covering classical-era GM games before engine-assist tooling was widely available. (Lower priority — only if (1) + (2) don't reach 50 games in scope.)

Each fixture's `.provenance.json` records: `source` (event URL or PGN archive identifier), `retrieved_at`, `label = "clean"`, `label_confidence = "high"` (for OTB and streamed) or `"medium"` (for pre-2010 archive — high but not directly observed at play time), and `notes`.

**Rationale**:
- OTB broadcast games are the strongest "verified clean" label available: physical arbiters, anti-cheat measures (detection equipment), and post-game scrutiny.
- Streamed top-player games are continuously observed by a large audience — undetected sustained cheating is implausible.
- Pre-engine-era games are a fallback only because the rating distribution may not match modern player demographics, slightly skewing the FPR measurement toward the high end of the rating buckets.

**Alternatives considered**:
- *Random sampling from Lichess month-export*: rejected. Label confidence is unknown (some sampled accounts may be undetected cheaters); contaminates the FPR measurement.
- *Synthetic "perfect human" games (engine-detuned)*: rejected for same reason as engine-assisted synthetic — distribution mismatch.

---

## R5 — Engine-Analysis Cache Design (for FPR-Gate CI Job)

**Decision**: Cache per-fixture engine analysis results under `tests/fixtures/corpora/.cache/<fixture_sha256>.json`. The cache key is the sha256 of the fixture PGN file (NOT the audit output) so any rebuild of the audit pipeline reuses the engine analysis. Use `actions/cache@v4` in CI to persist `.cache/` between runs, keyed by `engine_binary_sha256 + opening_book_sha256 + content of corpora/` (so any change to the engine, the book, or the corpus invalidates the cache).

**Rationale**:
- Engine analysis is the dominant cost (≈ 0.5-2.0 s per ply per the constitution). 70 fixtures × ~80 plies × 1 s ≈ 5500 s cold-cache. Warm cache reduces to JSON loading time (≈ milliseconds per fixture).
- Keying by fixture sha256 is robust: any edit to a PGN invalidates only that one fixture; corpus growth (adding fixtures) doesn't invalidate existing cache entries.
- CI-level cache key includes the engine and book sha256 so any algorithm-relevant change (engine upgrade, book replacement) properly busts the cache.

**Alternatives considered**:
- *Shared global cache keyed only by fixture sha256*: rejected. Engine binary updates would silently reuse stale analyses → false algorithm-validation results.
- *No cache, just always run cold*: rejected. CI cost becomes prohibitive (~90 min per PR per the cold estimate) and violates SC-005's 5-minute warm budget.

**Storage estimate**: 70 fixtures × ~200 KB per cached analysis JSON ≈ 14 MB. Well within GitHub Actions cache size limits (10 GB/repo).

---

## R6 — FPR / TPR Statistical Methodology

**Decision**: At the recommended scoring threshold (`SCORING_THRESHOLDS["strong-suspicion"]` from `packages/heuristics/src/heuristics/scoring/thresholds.py`):
- **FPR** = (# clean-corpus games whose `score.score` ≥ threshold) / (total clean-corpus games)
- **TPR** = (# engine-assisted-corpus games whose `score.score` ≥ threshold) / (total engine-assisted-corpus games)

Threshold passes if `FPR ≤ 0.020` AND `TPR ≥ 0.800`. The test asserts on the **point estimates** (no Wilson interval bounds for v2.0.0), but records exact-binomial 95% CIs in the diagnostic output for human review.

**Rationale**:
- Point-estimate gating with cushion (target ≤ 1.5%, gate ≤ 2.0%) per the Clarifications session is simpler than interval gating and aligned with the Phase 1 CUSUM 1.5%/1.0% convention.
- 95% CI in the diagnostic output gives reviewers a way to interpret near-threshold results without making the gate itself stochastic.
- With n = 50 clean games, an observed FPR of 0% gives 95% CI [0%, 7.1%]; observed 2% gives [0.05%, 10.6%]. The corpus size is modest — Phase 3 may need to expand it for tighter intervals.

**Alternatives considered**:
- *Wilson upper-bound gating*: more rigorous statistically but creates harder-to-debug gate behavior. Reserved for a future revision.
- *Bayesian posterior with prior*: out of scope for Phase 2.

**Diagnostic format on failure** (per SC-006):
```text
FPR gate FAILED:
  clean corpus:    FPR = 4.0% (2/50), threshold ≤ 2.0% [95% CI: 0.5%–13.7%]
  engine-assisted: TPR = 75.0% (15/20), threshold ≥ 80.0% [95% CI: 50.9%–91.3%]

Offending clean-corpus fixtures (FP):
  - tests/fixtures/corpora/clean/2024-tata-steel-r3-game7.pgn  (score=0.78)
  - tests/fixtures/corpora/clean/2025-otb-stream-blitz12.pgn   (score=0.84)

Missed engine-assisted fixtures (FN):
  - tests/fixtures/corpora/engine_assisted/lichess-banned-2024-01-15-acc1234.pgn (score=0.41)
  ...
```

---

## R7 — `AuditRun.manifest` Field Addition Strategy

**Decision**: Add an optional field `manifest: ReproducibilityManifest | None = None` to `AuditRun` in `packages/shared-types/src/shared_types/audit_run.py`. Populate it in `_build_run` (and the batch equivalent) at the same moment `_persist` writes the standalone `manifest.json` file. Existing consumers that don't read the field are unaffected (additive).

**Rationale**:
- The schema fields (`rating_baselines_sha256`, `signal_versions`, etc.) already exist on `ReproducibilityManifest`; the file `manifest.json` on disk already includes them; the only gap is that the in-memory `AuditRun` object passed back to CLI / frontend does not carry the manifest, so `--output json` envelopes are missing manifest provenance unless the consumer separately loads `manifest.json` from disk.
- Adding an optional field is additive and non-breaking: `AuditRun` is `frozen=False, extra="forbid"` so adding the field is a normal pydantic schema evolution. Old JSONs deserialize fine (field defaults to None).
- Single attachment site (`_build_run`) keeps the change localized.

**Alternatives considered**:
- *Continue reading `manifest.json` from disk in every consumer*: rejected. Couples consumers to the on-disk layout and is the source of the current bug (frontend/CLI JSON envelope doesn't include manifest).
- *Make `AuditRun.manifest` required (non-optional)*: rejected. Existing test fixtures / older AuditRun objects in cache directories would fail validation.

---

## R8 — Phase 1 T010 Status Reconciliation

**Decision**: Phase 1 T010 was marked "partial" with the rationale that `ReproducibilityManifest` schema changes were out of scope. **In practice**, the schema (`packages/shared-types/src/shared_types/report.py`) already includes `rating_baselines_sha256`, `rating_baselines_version`, `scoring_thresholds_version`, and `signal_versions` fields (verified during this plan). The `build_manifest` factory (`packages/analysis-core/src/analysis_core/manifest.py`) accepts and passes them through. The pipeline (`packages/analysis-core/src/analysis_core/pipeline/run.py`) computes and passes them to `build_manifest`. The `manifest.json` written to disk by `_persist` contains them.

The actual residual gap is narrower than the T010 note implied: only the `AuditRun` in-memory model lacks a `manifest` field, so the JSON envelope returned by the audit pipeline does not include manifest provenance. R7 closes this gap.

**Action for Phase 2 spec**: US4 / FR-003 / FR-004 are reframed in the tasks list to focus on the `AuditRun.manifest` field add and round-trip test rather than schema extension. Spec.md need not be amended — the FRs as written are satisfied by R7's implementation.

**Rationale**: Drift between the Phase 1 task-status notes and the actual code state is expected at this scale; reconciling here lets Phase 2 ship the smallest correct change rather than redoing already-done work.

---

## Summary

All eight research questions resolved. No outstanding `NEEDS CLARIFICATION` markers. Phase 1 design can proceed.
