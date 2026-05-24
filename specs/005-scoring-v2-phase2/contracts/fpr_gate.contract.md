# FPR Gate Contract — Feature 005

**Branch**: `005-scoring-v2-phase2`

This contract defines the shape, semantics, and pass/fail conditions of the labeled-corpus FPR gate (US3, FR-006, SC-003, SC-006).

---

## Test target

Path: `tests/fixtures/corpora/test_fpr_gate.py`.

Pytest collection name: `test_fpr_gate` (single test function — atomic pass/fail).

Invocation: `pytest tests/fixtures/corpora/test_fpr_gate.py -v`.

Invokes from CI under the new `fpr_gate` workflow job (`.github/workflows/ci.yml`).

---

## Inputs

1. **Corpus tree**: every `*.pgn` file under `tests/fixtures/corpora/clean/` and `tests/fixtures/corpora/engine_assisted/`, with a sibling `*.provenance.json` validated against `contracts/provenance.schema.json`.
2. **Engine analysis cache**: read from `tests/fixtures/corpora/.cache/<fixture_sha256>.json` if present; populated on cache miss.
3. **Threshold values**:
   - `FPR_THRESHOLD = 0.020` (per Clarifications session 2026-05-24).
   - `TPR_THRESHOLD = 0.800` (per Clarifications session 2026-05-24).
   - `SCORE_DECISION_THRESHOLD` = the value of `SCORING_THRESHOLDS["strong-suspicion"]` from `packages/heuristics/src/heuristics/scoring/thresholds.py` at test time.

---

## Procedure

For each fixture (clean and engine-assisted):

1. Compute `fixture_sha256 = sha256(PGN bytes)`.
2. Cache lookup at `tests/fixtures/corpora/.cache/<fixture_sha256>.json`.
   - **Hit**: load the cached `AuditRun` JSON.
   - **Miss**: run `cleanmatch audit-game <pgn> --output json` (or invoke the audit pipeline directly), persist the result to the cache file, then proceed.
3. Compare `audit_run.score.score` (the aggregate suspicion ∈ [0, 1]) against `SCORE_DECISION_THRESHOLD`.
4. Classify:
   - clean fixture with `score ≥ threshold` → **false positive (FP)**.
   - clean fixture with `score < threshold` → true negative.
   - engine-assisted fixture with `score ≥ threshold` → true positive.
   - engine-assisted fixture with `score < threshold` → **false negative (FN)**.

After all fixtures:

- `FPR = #FP / #clean_corpus`
- `TPR = #TP / #engine_assisted_corpus`
- 95% exact-binomial CIs for both (informational only; not gating).

Gate passes iff `FPR ≤ FPR_THRESHOLD AND TPR ≥ TPR_THRESHOLD`.

---

## Output (on failure)

Emit to stderr (and to a `fpr_gate_report.json` artifact in CI):

```text
FPR gate FAILED:
  clean corpus:    FPR = 4.0% (2/50), threshold ≤ 2.0% [95% CI: 0.5%–13.7%]
  engine-assisted: TPR = 75.0% (15/20), threshold ≥ 80.0% [95% CI: 50.9%–91.3%]

False positives (clean games flagged as suspect):
  - tests/fixtures/corpora/clean/2024-tata-steel-r3-game7.pgn  (score=0.78)
  - tests/fixtures/corpora/clean/2025-otb-stream-blitz12.pgn   (score=0.84)

False negatives (engine-assisted games missed):
  - tests/fixtures/corpora/engine_assisted/lichess-banned-2024-01-15-acc1234.pgn (score=0.41)
  ...
```

Structured form (always written to `fpr_gate_report.json`, regardless of pass/fail):

```jsonc
{
  "passed": false,
  "fpr": 0.04,
  "fpr_threshold": 0.02,
  "fpr_ci_95": [0.005, 0.137],
  "tpr": 0.75,
  "tpr_threshold": 0.80,
  "tpr_ci_95": [0.509, 0.913],
  "clean_corpus_size": 50,
  "engine_assisted_corpus_size": 20,
  "score_decision_threshold": 0.55,
  "false_positives": [
    {"fixture": "tests/fixtures/corpora/clean/2024-tata-steel-r3-game7.pgn", "score": 0.78},
    {"fixture": "tests/fixtures/corpora/clean/2025-otb-stream-blitz12.pgn",   "score": 0.84}
  ],
  "false_negatives": [
    {"fixture": "tests/fixtures/corpora/engine_assisted/lichess-banned-2024-01-15-acc1234.pgn", "score": 0.41}
  ],
  "thresholds_version": "2.0.0"
}
```

---

## Performance budget (Principle IV)

- Warm cache (all `.cache/*.json` present): wall time ≤ **5 minutes** on a standard GitHub runner (SC-005).
- Cold cache (full re-analysis): wall time ≤ **30 minutes** (SC-005).
- Cache invalidation key (set by CI): `engine_binary_sha256 ⊕ opening_book_sha256 ⊕ tree-hash of tests/fixtures/corpora/{clean,engine_assisted}/`. Any change to the engine, the book, or the corpus content busts the cache and forces a cold-cache run.

---

## Stability guarantees

- The gate is **deterministic**: same corpus + same engine + same book + same seeds ⇒ identical `fpr_gate_report.json` byte-for-byte.
- Adding a new fixture (or fixing a `.provenance.json` typo) does not invalidate existing cache entries because the cache is keyed by per-fixture sha256.
- Phase 2 algorithm changes are explicitly forbidden (FR-010). If the gate fails on the shipping corpus, the remediation is Phase 3 algorithm tuning, not threshold relaxation.

---

## Test fixtures (this contract)

A small synthetic mini-corpus under `tests/fixtures/corpora/_smoke/` (gitignored from the FPR-gate test discovery) is used by unit tests of the gate target itself — verifying that classification, CI computation, and diagnostic output are correct independently of the real corpus.
