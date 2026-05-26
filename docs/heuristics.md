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

## Building rating_baselines.json (T007 v2 — Postgres-backed)

`packages/heuristics/scripts/build_baselines.py` derives the seven
`rating_baselines.json` buckets from a Lichess monthly export. Feature
007 v2 (2026-05-26) persists every Stockfish analysis to Postgres as it
completes, so a multi-hour run survives any single crash.

### Prerequisites

```bash
# 1. Postgres up (feature 008 infrastructure)
podman compose -f infra/docker/compose.yml up -d postgres

# 2. Stockfish 16 container image
podman build -t cleanmatch-stockfish:sf16 -f infra/docker/stockfish.Containerfile .

# 3. Lichess monthly archive (NEVER commit — gitignored)
curl -O https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst

# 4. Database URL exported
export DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch

# 5. Schema up to date
uv run alembic -c packages/analysis-core/alembic.ini upgrade head
```

### Fresh run

```bash
uv run python packages/heuristics/scripts/build_baselines.py \
    --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst \
    --workers 6 \
    --depth 10 \
    --multipv 3 \
    --seed 0 \
    --per-bucket-sample 5000
```

The script INSERTs one `baseline_runs` row (status='running'), streams
the 89M-game archive flushing reservoir state every 100k games, then
spawns 6 workers that drain `baseline_samples` via `SELECT FOR UPDATE
SKIP LOCKED`. ~21 min Phase 1 + ~5.5 h Phase 2 on a 6-core machine.

### Resume after a crash

```bash
# Find the running/aborted run
podman exec cleanmatch-postgres psql -U cleanmatch -d cleanmatch -c \
  "SELECT id, status, total_scanned, total_sampled, total_analysed
   FROM baseline_runs ORDER BY started_at DESC LIMIT 5"

# Resume — Phase 1 skipped, workers re-claim pending or stale samples
uv run python packages/heuristics/scripts/build_baselines.py \
    --run-id <uuid-from-query>
```

Workers re-claim any sample whose `claimed_at` is older than 15 min and
whose `analysed = FALSE`. No double work; trigger flips `analysed=TRUE`
when a `baseline_analyses` row lands.

### Inspecting progress

```bash
podman exec cleanmatch-postgres psql -U cleanmatch -d cleanmatch -c \
  "SELECT status, total_scanned, total_sampled, total_analysed,
          (NOW() - started_at) AS elapsed
   FROM baseline_runs ORDER BY started_at DESC LIMIT 1"
```

### Production dump

The run + its samples + analyses + the PGN corpus are dumpable for
re-deployment without rerunning Stockfish:

```bash
pg_dump $DATABASE_URL \
    --table=baseline_runs \
    --table=baseline_samples \
    --table=baseline_analyses \
    --table=pgn_corpus \
    -Fc -f "baselines-$(date -I).dump"
```

Restore on the target host:

```bash
createdb cleanmatch
uv run alembic -c packages/analysis-core/alembic.ini upgrade head
pg_restore --data-only -d $DATABASE_URL baselines-2026-05-26.dump
```

Then re-run the script with `--run-id` pointing at the restored row —
or just SELECT from `baseline_buckets` to materialise
`rating_baselines.json` without a script invocation.
