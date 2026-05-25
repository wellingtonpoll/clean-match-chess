# Heuristic Signals

Versioned signal modules drive every suspicion score. Each module
ships its `__signal_name__` + `__signal_version__` so the
reproducibility manifest pins exactly which version produced a given
report.

## v0.1.0 (MVP)

| Signal | Module | Description | Constitution principle |
|---|---|---|---|
| `complexity-analysis` | `heuristics.complexity_analysis` | Aggregates per-position `ComplexityScore.composite` over the analysed positions. Feeds the complexity-weighted match. | Principle 7 |
| `tactical-detection` | `heuristics.tactical_detection` | Fraction of positions flagged `is_critical` (only-move chains, in-check, large eval swings) minus the `is_only_move` set. | Principles 5, 7 |
| `regime-shift` | `heuristics.regime_shift` | Normalised max delta in segment sizes — proxy for behavioural shift across phases. | DRS §4 (behavioural) |
| `engine-correlation/top1` | `heuristics.engine_correlation` | Fraction of plies where the played move matched the engine's top choice. Book + only-move plies excluded. | Principles 4, 6 |
| `engine-correlation/top3` | `heuristics.engine_correlation` | Same as top1 with the top-3 candidate set. | Principle 4 |
| `engine-correlation/weighted` | `heuristics.engine_correlation` | Complexity-weighted top-1 match — the headline anti-cheat signal. | Principle 7 |
| `behavioral-patterns/precision-burst` | `heuristics.behavioral_patterns` | Longest streak of consecutive top-1 matches, normalised by game length. | DRS §4 |
| `behavioral-patterns/blunder-suppression` | `heuristics.behavioral_patterns` | Fraction of high-complexity positions with no significant blunder. | DRS §4 |
| `timing-analysis` | `heuristics.timing_analysis` | Fraction of moves played implausibly fast for the position's complexity. Silenced when timing data missing. | DRS §10 |

## Adding a new signal

1. Create a new package under `packages/heuristics/src/heuristics/<signal-name>/`.
2. Export `__signal_name__`, `__signal_version__`, `signal_version()`,
   and a pure computation function.
3. Add a unit test covering: empty input, in-range output, version
   surface.
4. Register the signal in `pipeline/run.py`'s default heuristic set.
5. If the signal contributes to the suspicion score, add it to
   `WEIGHTS` in `heuristics.scoring.aggregator`. Weights MUST sum to
   exactly 1.0.
6. Add a rationale template entry in `heuristics.scoring.narrative`.
7. Bump the signal's version per semver; update the changelog.

## Versioning policy

Per RNF-07: each signal carries its own semver. The
reproducibility manifest records the exact versions; consumers can
detect drift by diffing manifests across runs.

- **MAJOR**: removal or backward-incompatible semantic change.
- **MINOR**: new tunable, new sub-signal, expanded output.
- **PATCH**: bug fix, rationale-string refinement, perf improvement.

## Known limitations (v2.0.0)

- `Move.signal_contributions` is empty in the persisted run output;
  per-move attribution requires a second-pass injection in
  `pipeline/run.py`. Tracked.
- Rating-baseline calibration ships with literature-derived values
  (`packages/heuristics/data/rating_baselines.json`, `source_dataset =
  "hand-curated-stub"`, `sample_size = 100` per bucket). Feature 007
  replaces this with measured population stats from a Lichess monthly
  export (≥ 1000 games sampled per bucket via reservoir sampling at
  Stockfish-16 depth 12). Once 007 lands, `acpl-analysis` and
  `engine-correlation/weighted` will judge against measured human
  populations rather than estimates.
- Labeled-corpus FPR/TPR not yet measured. Feature 005 shipped the
  gate harness (`tests/fpr_gate/`) and 50 clean fixtures; feature 007
  sources ≥ 20 engine-assisted fixtures and runs the cold-cache gate.

## Resolved (past limitations)

- `OpeningBook` bundling — addressed in feature 004 (initial `gm2600.bin`
  stub) and re-shipped in feature 005 as a 6.5 MB Lichess-broadcast-derived
  book at `packages/analysis-core/data/opening_book.bin`. Plies in the
  book are now correctly flagged.
- `StaticAnalyzer`-only — feature 004 wired real `EngineAnalyzer`
  (Stockfish via `python-chess` UCI) at `packages/analysis-core/src/analysis_core/engine/analysis.py`.
  `StaticAnalyzer` is now a test-only fallback.

## Reproducibility

The aggregator's bootstrap CI is seeded (`seed=0` by default; CLI
exposes no seed override). Same engine fingerprint + same heuristic
versions + same input PGN SHA256 = bit-identical score on the same
CPU architecture. See FR-017.
