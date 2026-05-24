# Quickstart — Verifying Fraud Detection Algorithm v2 (Phase 1)

This guide walks through running an audit post-refactor and verifying the v2 algorithm is active.

## Prerequisites

- Repo at branch `004-scoring-v2-phase1` (or merged into `main` post-feature).
- `uv sync` complete.
- A Stockfish binary available locally OR the `cleanmatch-stockfish:quick` Podman image built.

## Step 1 — Run a single-game audit

```bash
cleanmatch audit-game tests/fixtures/regan_calibration_50.pgn \
  --subject white \
  --output json \
  --engine-path /usr/bin/stockfish
```

(Or substitute `--engine-image cleanmatch-stockfish:quick` if using Podman.)

## Step 2 — Verify v2 algorithm is active

In the emitted JSON, check:

1. **ACPL signal present**:

   ```bash
   ... | jq '.score.dominant_signals'
   ```

   Should contain `"acpl-analysis"` among the top-3 signals on most non-trivial games.

2. **Per-move `eval_delta_cp` populated**:

   ```bash
   ... | jq '.game.moves[] | .eval_delta_cp' | head -5
   ```

   Should return integers (not nulls) for non-book moves.

3. **Per-segment `signals` and `score_contribution` populated**:

   ```bash
   ... | jq '.segments[] | {phase, score_contribution, signal_count: (.signals | length)}'
   ```

   Each segment should have `signal_count > 0` and a numeric `score_contribution`.

4. **CI is narrower than before**:

   ```bash
   ... | jq '.score.confidence_interval'
   ```

   On a 100+ ply game, CI width (high - low) should be ≤ 0.20 (vs the old ~0.60).

5. **Manifest stamps the new versions**:

   ```bash
   ... | jq '.manifest | {scoring_thresholds_version, rating_baselines_version, opening_book_sha256, signal_versions}'
   ```

   Should show `scoring_thresholds_version: "2.0.0"`, a non-zero `rating_baselines_version`, a real `opening_book_sha256`, and `signal_versions["acpl-analysis"]` present.

## Step 3 — Rating calibration sanity check

Run the SAME PGN with two different `WhiteElo` headers and confirm scores differ. If the Elo header is missing or incorrect, edit the `WhiteElo` / `BlackElo` fields directly in a temp copy of the PGN before running the audit. No flag override is available in this release.

```bash
# Original PGN with WhiteElo = 1500
cleanmatch audit-game game_1500.pgn --subject white --output json | jq '.score.score'

# Same PGN content with WhiteElo = 2700 (manually edit header in a temp copy)
cleanmatch audit-game game_2700.pgn --subject white --output json | jq '.score.score'
```

Score for the 1500 version should be at least 0.25 higher than the 2700 version (SC-003).

## Step 4 — Opening book verification

Run with no `--book` flag (bundled default loads) vs `--book ""` (explicit no book, if supported):

```bash
# Default — bundled book loaded
cleanmatch audit-game tests/fixtures/italian_game.pgn --output json | \
  jq '.game.positions[:14] | map(.is_book) | unique'
# Expected: [true]

# Custom book path
cleanmatch audit-game tests/fixtures/italian_game.pgn --book /path/to/custom.bin --output json | \
  jq '.game.positions[:14] | map(.is_book) | unique'
# Expected: depends on custom book; should not crash
```

## Step 5 — Run all tests

```bash
# Heuristics package
uv run pytest packages/heuristics/

# Analysis-core package
uv run pytest packages/analysis-core/

# Full repo
uv run pytest
```

Expected: all green (the only modifications to existing tests should be re-pinned numeric expectations reflecting the v2 algorithm shift).

## Step 6 — Performance budget check

```bash
uv run python packages/heuristics/tests/bench_aggregator.py
```

Expected output: bootstrap N=10000 on a 200-ply game completes in ≤ 100 ms (constitution Principle IV).

## Step 7 — Determinism check

```bash
# Run twice with the same seed; outputs should be bit-identical
cleanmatch audit-game game.pgn --output json > run1.json
cleanmatch audit-game game.pgn --output json > run2.json
diff run1.json run2.json
# Expected: no diff
```

## Step 8 — Read the CHANGELOG

`CHANGELOG.md` v2.0.0 entry MUST state:
- Score values are NOT comparable to v1.x runs.
- New `acpl-analysis` signal added with weight 0.30.
- `blunder-suppression` bug fix.
- Bootstrap CI methodology changed.
- Bundled opening book + rating baselines included.

## Common issues

- **`acpl-analysis` missing from dominant_signals**: usually means the game is too short (< 10 non-book plies). Check `samples` field in the signal aggregate.
- **CI still wide on long games**: confirm `SCORING_THRESHOLDS_VERSION == "2.0.0"` in manifest. If still `1.0.0`, the bootstrap upgrade did not land.
- **`Position.is_book` always False**: verify the opening book file is present at `packages/analysis-core/data/opening_book.bin` and the sha256 matches the manifest entry.
