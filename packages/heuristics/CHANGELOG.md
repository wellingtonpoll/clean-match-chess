# Heuristics Changelog

All signal modules versioned independently. See `docs/heuristics.md`
for the per-signal table.

## Unreleased (Feature 005 Phase 2)

No signal version changes (FR-010). When `rating_baselines.json` is
regenerated from real Lichess 2026-04 data (feature 005 US1), this entry
will record the dataset URL + sha256 and the smoke-test score delta vs
the Phase 1 stub baseline.

## 2.0.0 — 2026-05-24 (Feature 004 Phase 1)

Per-signal bumps and rationale:

- `acpl-analysis@1.0.0` — NEW. Rating-bucket-calibrated ACPL signal
  (FR-002, FR-003).
- `behavioral-patterns@2.0.0` — `blunder-suppression` rewritten with
  delta-based expected-blunder definition (FR-004 fix; the v1
  implementation tautologically counted "post-move position is calm").
- `regime-shift@2.0.0` — CUSUM change-point detection on per-move
  ACPL series replaces the segment-size variation metric (FR-005).
- `timing-analysis@2.0.0` — OLS regression of `log(time_ms+1) ~
  complexity + phase` with residual-threshold + premove sub-signal
  replaces the binary fast-move count (FR-006).
- `engine-correlation@2.0.0` — adds rating-bucket calibrated ratio
  mode (raw rate in `mean`, ratio in `weighted_mean`); top-3 is
  silenced in calibrated mode pending an expected-top3 baseline
  (FR-008).
- `WEIGHTS` redistribution per FR-016 (sum 1.0 across per-signal keys);
  carrier `segments-weighted-aggregate` added at 0.74.

## 0.1.0 — 2026-05-23 (MVP)

Initial signal set:

- `complexity-analysis@0.1.0`
- `tactical-detection@0.1.0`
- `regime-shift@0.1.0`
- `engine-correlation@0.1.0` (`top1`, `top3`, `weighted` sub-aggregates)
- `behavioral-patterns@0.1.0` (`precision-burst`, `blunder-suppression` sub-aggregates)
- `timing-analysis@0.1.0`

Aggregator weights locked in `heuristics.scoring.aggregator.WEIGHTS`:

| Signal | Weight |
|---|---|
| engine-correlation/weighted | 0.50 |
| engine-correlation/top1 | 0.15 |
| engine-correlation/top3 | 0.05 |
| regime-shift | 0.10 |
| tactical-detection | 0.05 |
| complexity-analysis | 0.05 |
| behavioral-patterns/precision-burst | 0.05 |
| behavioral-patterns/blunder-suppression | 0.03 |
| timing-analysis | 0.02 |

Risk thresholds: low <0.35, medium [0.35, 0.70), high ≥0.70 (locked
by spec Clarification Q1, 2026-05-23).
