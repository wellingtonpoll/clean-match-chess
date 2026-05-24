# Data Model — Feature 005 (Scoring v2 Phase 2)

**Branch**: `005-scoring-v2-phase2` | **Date**: 2026-05-24

Phase 2 introduces two new data artifacts and one schema delta. Existing scoring/signal/segment data structures are unchanged (FR-010).

---

## 1. `AuditRun.manifest` (new optional field)

**Location**: `packages/shared-types/src/shared_types/audit_run.py`

**Change**:

```python
from shared_types.report import ReproducibilityManifest

class AuditRun(BaseModel):
    model_config = ConfigDict(frozen=False, extra="forbid")
    # ... existing fields ...
    manifest: ReproducibilityManifest | None = None  # NEW
```

**Semantics**:
- `None` ⇔ AuditRun was constructed without manifest attachment (e.g., legacy cached runs, ad-hoc tests). Consumers treat this as "manifest unavailable in-band; load `manifest.json` from disk if reproducibility provenance is required."
- Non-None ⇔ full manifest is embedded; consumers can read `audit_run.manifest.rating_baselines_sha256`, `audit_run.manifest.signal_versions["acpl-analysis"]`, etc. directly.

**Validation**:
- Pydantic v2 round-trip: an `AuditRun` serialized with a populated `manifest` and deserialized back must yield byte-identical manifest fields (covered by a new unit test).
- No mutation post-construction (pipeline sets the field exactly once in `_build_run`, before returning).

**Backward compatibility**:
- Existing `~/.cleanmatch/runs/<id>/run.json` files written before this change have no `manifest` key. Loading them with the new schema works because the field defaults to None. No migration script needed.

---

## 2. `tests/fixtures/corpora/*.provenance.json` (new artifact)

**Location**: Sibling file next to every PGN in `tests/fixtures/corpora/clean/` and `tests/fixtures/corpora/engine_assisted/`. Naming: `<pgn_filename_without_extension>.provenance.json`. Example: `2024-tata-steel-r3-game7.pgn` → `2024-tata-steel-r3-game7.provenance.json`.

**Schema** (formal JSON schema at `contracts/provenance.schema.json`):

```jsonc
{
  "source": "https://example.com/event-or-account-url",
  "retrieved_at": "2026-04-15T12:34:56Z",
  "label": "clean",                    // or "engine_assisted"
  "label_confidence": "high",          // "high" | "medium" | "low"
  "notes": "OTB game from official broadcast PGN; arbiter-monitored."
}
```

**Field semantics**:

| Field | Type | Required | Notes |
|---|---|---|---|
| `source` | string (URL or identifier) | yes | Canonical URL of the source event, account, or archive. Identifier acceptable if URL would be ambiguous (e.g., "ChessBase MegaBase 2024 game 1234567"). |
| `retrieved_at` | string (ISO 8601 UTC) | yes | When the PGN was downloaded to the repo. Used to document staleness for re-validation. |
| `label` | enum: `"clean"` \| `"engine_assisted"` | yes | The ground-truth label used by the FPR-gate test. |
| `label_confidence` | enum: `"high"` \| `"medium"` \| `"low"` | yes | Reviewer confidence in the label (not statistical confidence). High = arbiter/system-confirmed; medium = strong contextual evidence; low = inferred. The FPR-gate test MAY filter by confidence in future revisions. |
| `notes` | string | yes (may be empty) | Free-form caveats. **For engine-assisted Lichess fixtures**: MUST include a sentence acknowledging the circularity risk noted in `spec.md` Edge Cases. |

**Validation**:
- Every PGN under `tests/fixtures/corpora/clean/` or `.../engine_assisted/` MUST have a sibling `.provenance.json`. The FPR-gate test fails fast if any PGN is missing its provenance.
- Pydantic model `ProvenanceRecord` in the test target validates structure on load. Schema lives at `contracts/provenance.schema.json` for offline tooling reference.

---

## 3. Rating Baselines Refresh (no schema change)

**Location**: `packages/heuristics/data/rating_baselines.json`

**Change**: Content regenerated from real Lichess 2026-04 data. Schema unchanged (already at `packages/heuristics/contracts/rating_baselines.schema.json`).

**Expected delta from Phase 1 stub**:
- `source_dataset` shifts from `"hand-curated-stub (Phase 1 fallback; lit. values, not measured)"` to a string referencing `https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst` + retrieval date.
- Per-bucket `sample_size` shifts from 100 (stub) to ≥ 1000 (real).
- Per-bucket `expected_*` values shift to whatever the real dataset produces (no a-priori claim on direction).
- `sha256` of the file changes → `manifest.rating_baselines_sha256` shifts for all audits.

---

## 4. Opening Book Refresh (no schema change)

**Location**: `packages/analysis-core/data/opening_book.bin`

**Change**: 1.3 KB stub replaced by real `gm2600.bin` (~1 MB+). Polyglot binary format unchanged.

**Expected delta from Phase 1 stub**:
- File size grows by 1000×.
- sha256 changes → `manifest.opening_book_sha256` shifts for all audits.
- `OpeningBook.contains(board)` returns True for the first ~12 plies of standard openings (Italian, Sicilian, Ruy Lopez, etc.) where it returned False under the stub.

`packages/analysis-core/data/README.md` is updated to record the real upstream URL + retrieval date + new sha256.

---

## 5. FPR-Gate Test Output (structured diagnostic)

**Location**: pytest output of `tests/fixtures/corpora/test_fpr_gate.py`.

**Format**: Plain text on stdout (per constitution Principle III — human-readable error). When `--log-format=json` is in effect, the same data is emitted as a single JSON line. Shape:

```jsonc
{
  "fpr": 0.04,
  "fpr_threshold": 0.02,
  "tpr": 0.75,
  "tpr_threshold": 0.80,
  "clean_corpus_size": 50,
  "engine_assisted_corpus_size": 20,
  "fpr_ci_95": [0.005, 0.137],
  "tpr_ci_95": [0.509, 0.913],
  "false_positives": [
    {"fixture": "tests/fixtures/corpora/clean/...", "score": 0.78},
    {"fixture": "tests/fixtures/corpora/clean/...", "score": 0.84}
  ],
  "false_negatives": [
    {"fixture": "tests/fixtures/corpora/engine_assisted/...", "score": 0.41}
  ],
  "passed": false
}
```

Contract specification at `contracts/fpr_gate.contract.md`.

---

## Entities Inventory (cross-reference vs Phase 1)

| Entity | Phase 1 status | Phase 2 change |
|---|---|---|
| `Move`, `Position`, `Segment`, `Game`, `Player`, `Score`, `SignalAggregate`, `HeuristicVersion` | stable | unchanged |
| `ReproducibilityManifest` | schema fields present (incl. `rating_baselines_sha256`, `signal_versions`) | unchanged (verified — Phase 1 T010 partial note was stale; see research.md R8) |
| `AuditRun` | no `manifest` field | NEW optional field `manifest: ReproducibilityManifest \| None = None` |
| `ProvenanceRecord` | does not exist | NEW pydantic model (test-side only; not part of shared-types since it's a fixtures-tree concept) |
