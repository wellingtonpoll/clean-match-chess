# Phase 1 Data Model — Fraud Detection Algorithm v2 (Phase 1)

## Existing entities (no schema changes)

These are part of `packages/shared-types/src/shared_types/` and are referenced by this feature without modification.

- `Position` (game.py) — already declares `is_book: bool` and `complexity: ComplexityScore`. Phase 1 populates `is_book` from the opening book (was always False before).
- `Move` (game.py) — already declares `eval_delta_cp: int | None`. Phase 1 populates it (was always None before).
- `Segment` (signal.py) — already declares `signals: tuple[SignalAggregate, ...]` and `score_contribution: float | None`. Phase 1 populates both (were empty/None).
- `SignalAggregate` (signal.py) — unchanged. Phase 1 produces new instances with new `signal_name` values.
- `SuspicionScore` (score.py) — unchanged. CI semantics tighten in Phase 1 (narrower intervals from the new bootstrap) but the field shape is identical.
- `ComplexityScore` (game.py) — unchanged.

## New entities (added by this feature)

### `AcplStats`

Internal computation type used by `acpl_analysis/`.

```python
@dataclass(frozen=True, slots=True)
class AcplStats:
    observed_mean: float          # Mean of max(0, -eval_delta_cp) over eligible plies
    observed_stdev: float         # Standard deviation of same
    sample_count: int             # Number of plies counted
    expected_mean: float          # From rating-baselines lookup for player's bucket
    expected_stdev: float         # From rating-baselines lookup for player's bucket
    rating_bucket_label: str      # E.g. "1501-1800" or "rating-unknown"
    suspicion_value: float        # In [0, 1]; 1.0 = ≥3σ below expected (very suspicious)
```

`suspicion_value` formula:

```
z = (expected_mean - observed_mean) / expected_stdev
suspicion_value = max(0.0, min(1.0, z / 3.0))
```

Interpretation: observed ACPL 3 standard deviations below the expected mean → suspicion_value 1.0. Observed ACPL at or above expected mean → suspicion_value 0.0.

### `RatingBaseline`

One entry in the bundled `rating_baselines.json` lookup. Pure data; no behaviour.

```python
@dataclass(frozen=True, slots=True)
class RatingBaseline:
    bucket_label: str             # E.g. "1501-1800" or "rating-unknown"
    rating_low: int | None        # Lower bound (inclusive), None for unknown bucket
    rating_high: int | None       # Upper bound (inclusive), None for top + unknown buckets
    expected_top1: float          # Population mean of top-1 match rate for this bucket
    expected_weighted_top1: float # Population mean of complexity-weighted top-1 for this bucket
    expected_acpl_mean: float     # Population mean of ACPL for this bucket
    expected_acpl_stdev: float    # Population stdev of ACPL for this bucket
    sample_size: int              # Games used to derive the population stats
```

### `RatingBaselines`

Container loaded once at module-import time.

```python
@dataclass(frozen=True, slots=True)
class RatingBaselines:
    version: str                                          # Semver, e.g. "1.0.0"
    generated_at: str                                     # ISO 8601 UTC
    source_dataset: str                                   # E.g. "lichess-db-2025-06"
    buckets: tuple[RatingBaseline, ...]                   # Always 7 entries: 6 buckets + unknown

    def bucket_for(self, rating: int | None) -> RatingBaseline: ...
    def for_label(self, bucket_label: str) -> RatingBaseline: ...
```

`bucket_for(rating)` returns:
- The matching `RatingBaseline` whose `[rating_low, rating_high]` contains `rating`.
- The `"rating-unknown"` entry when `rating is None` or rating outside `[1, 3500]`.

### `CusumChangePoint`

A single detected change point in the per-move ACPL series. Used by the rewritten `regime_shift_score`.

```python
@dataclass(frozen=True, slots=True)
class CusumChangePoint:
    ply_index: int                # 0-based index in the ACPL series
    cumulative_deviation: float   # Magnitude S_t at detection
    direction: Literal["improvement", "regression"]
```

Embedded into the `SignalAggregate.weighted_mean` is the count of change points scaled to [0, 1] by `min(1.0, count / 3.0)`.

### `SegmentScore`

Computed by the new `segment_aggregator.py`. Not persisted directly — its values flow into `Segment.signals` and `Segment.score_contribution`.

```python
@dataclass(frozen=True, slots=True)
class SegmentScore:
    phase: SegmentPhase                                   # OPENING/MIDDLEGAME/TACTICAL/CONVERSION/ENDGAME
    raw_aggregate: float                                  # In [0, 1] — weighted mean of per-segment signals
    phase_weight: float                                   # E.g. TACTICAL → 1.5
    weighted_contribution: float                          # raw_aggregate * phase_weight
    signals: tuple[SignalAggregate, ...]                  # Per-segment heuristic outputs
```

## Lookup table schema (committed)

File: `packages/heuristics/data/rating_baselines.json`. Schema in `contracts/rating_baselines.schema.json` (strict, `additionalProperties: false`).

Buckets (six rated + one fallback):

| bucket_label | rating_low | rating_high |
|---|---|---|
| `≤1200` | 1 | 1200 |
| `1201-1500` | 1201 | 1500 |
| `1501-1800` | 1501 | 1800 |
| `1801-2100` | 1801 | 2100 |
| `2101-2400` | 2101 | 2400 |
| `2401+` | 2401 | 3500 |
| `rating-unknown` | null | null |

The `"rating-unknown"` bucket's expected values are set to the median across the six rated buckets.

## Opening book file format

`packages/analysis-core/data/opening_book.bin` is a standard polyglot `.bin` file (specification: https://www.chessprogramming.org/PolyGlot). Read via `chess.polyglot.MemoryMappedReader(path)`. Each entry is `(key: uint64, move: uint16, weight: uint16, learn: uint32)`. Phase 1 uses only `key` and `weight`; a position is considered "in book" if `reader.get(board)` returns an entry with `weight > 0`.

Manifest stamping: sha256 of the book file is computed at audit start and included in the run manifest.

## Modified existing files (field-level summary)

| File | Field | Change |
|---|---|---|
| `shared_types/game.py::Move.eval_delta_cp` | Existing | None at schema level; pipeline now populates it (was always None). |
| `shared_types/game.py::Position.is_book` | Existing | None at schema level; pipeline now sets True for book positions (was always False). |
| `shared_types/signal.py::Segment.signals` | Existing | None at schema level; segment_aggregator now populates it (was empty tuple). |
| `shared_types/signal.py::Segment.score_contribution` | Existing | None at schema level; segment_aggregator now populates it (was None). |
| `heuristics/scoring/aggregator.py::WEIGHTS` | Existing | Dict contents change — new key `acpl-analysis: 0.30`, reduced `engine-correlation/top1: 0.05`, full redistribution per FR-016. |
| `heuristics/scoring/thresholds.py::SCORING_THRESHOLDS_VERSION` | Existing | String value bumps `"1.0.0"` → `"2.0.0"`. |

## Persisted JSON shape (audit run export)

No keys removed. New keys (additive only):

```jsonc
{
  // ... existing keys ...
  "segments": [
    {
      "phase": "TACTICAL",
      "ply_range": [22, 47],
      // NEW — was always [] before:
      "signals": [
        {"signal_name": "acpl-analysis", "mean": 0.78, "samples": 26, ...},
        {"signal_name": "engine-correlation/weighted", "mean": 0.81, "samples": 26, ...},
        // ...
      ],
      // NEW — was always null before:
      "score_contribution": 0.187
    }
  ],
  "manifest": {
    // ... existing keys ...
    // NEW:
    "opening_book_sha256": "abc123...",
    "rating_baselines_version": "1.0.0",
    "rating_baselines_sha256": "def456...",
    "scoring_thresholds_version": "2.0.0",
    "signal_versions": {
      "acpl-analysis": "1.0.0",
      "regime-shift": "2.0.0",     // bumped from 0.1.0 because algorithm changed
      "timing-analysis": "2.0.0",  // bumped from 0.1.0 because algorithm changed
      // others unchanged
    }
  }
}
```
