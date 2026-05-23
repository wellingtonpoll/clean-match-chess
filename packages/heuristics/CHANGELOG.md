# Heuristics Changelog

All signal modules versioned independently. See `docs/heuristics.md`
for the per-signal table.

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
