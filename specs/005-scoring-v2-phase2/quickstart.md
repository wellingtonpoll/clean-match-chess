# Quickstart — Feature 005 (Scoring v2 Phase 2)

**Branch**: `005-scoring-v2-phase2` | **Date**: 2026-05-24

Maintainer-facing recipes for the three artifact-refresh + corpus tasks. Each step assumes you have a clean checkout of `005-scoring-v2-phase2` and that Phase 1 dependencies (numpy, python-chess, pydantic v2) are installed via `uv sync`.

---

## 1. Refresh `rating_baselines.json` from real Lichess data (US1)

```bash
# 1. Download the 2026-04 month-export (multi-GB; expect 10-30 min on residential bandwidth)
curl -L -o /tmp/lichess_2026-04.pgn.zst \
  https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst

# 2. Decompress (zstd required: `apt install zstd` or `brew install zstd`)
zstd -d /tmp/lichess_2026-04.pgn.zst -o /tmp/lichess_2026-04.pgn

# 3. Run the build script (expect 30-90 min depending on hardware; uses python-chess in single-threaded streaming mode)
uv run python packages/heuristics/scripts/build_baselines.py \
  --input /tmp/lichess_2026-04.pgn \
  --output packages/heuristics/data/rating_baselines.json \
  --source-label "lichess_db_standard_rated_2026-04"

# 4. Verify schema validates and per-bucket sample_size >= 1000
uv run python -c "
from heuristics.rating_baselines import get_baselines
b = get_baselines()
for bucket in b.buckets:
    assert bucket.sample_size >= 1000, f'{bucket.bucket_label} sample_size={bucket.sample_size}'
    print(f'{bucket.bucket_label}: n={bucket.sample_size}, ACPL μ={bucket.expected_acpl_mean:.1f}')
print('OK')
"

# 5. Compute and stash the new sha256 for the CHANGELOG
sha256sum packages/heuristics/data/rating_baselines.json
```

**Acceptance** (US1 AS1/AS2/AS3):
- `source_dataset` field references the real dataset URL + date.
- All buckets `sample_size ≥ 1000`.
- Schema validator passes (no drift introduced by real data).

---

## 2. Refresh `opening_book.bin` with real `gm2600.bin` (US2)

```bash
# 1. Download from the canonical source (record the exact URL you used)
curl -L -o /tmp/gm2600.bin \
  https://github.com/michaelb/Sayuri-chess-bot/raw/main/books/gm2600.bin

# 2. Compute sha256 and compare against the upstream-documented value
ACTUAL_SHA=$(sha256sum /tmp/gm2600.bin | cut -d' ' -f1)
echo "Downloaded sha256: $ACTUAL_SHA"
# Expected: see packages/analysis-core/data/README.md for the canonical value;
# if README.md doesn't yet have one (Phase 1 stub), record $ACTUAL_SHA here as the new canonical.

# 3. Replace the stub
cp /tmp/gm2600.bin packages/analysis-core/data/opening_book.bin

# 4. Update README.md with source URL, retrieval date, and sha256 (manual edit)
# (e.g., add: "Source: https://...; retrieved 2026-04-15; sha256: $ACTUAL_SHA")

# 5. Verify book coverage on the smoke-test PGN
uv run python -c "
from analysis_core.pipeline.opening_book import OpeningBook
import chess.pgn, io
book = OpeningBook.load()
pgn = open('tests/fixtures/audit_v2_smoke.pgn').read()
game = chess.pgn.read_game(io.StringIO(pgn))
board = game.board()
book_plies = 0
for move in game.mainline_moves():
    if book.contains(board):
        book_plies += 1
    board.push(move)
print(f'book_plies: {book_plies}  (expect >= 12 for standard openings)')
assert book_plies >= 12, 'book coverage too low — possibly wrong file'
print('OK')
"
```

**Acceptance** (US2 AS1/AS2/AS3):
- File size ≥ 1 MB.
- sha256 recorded in `packages/analysis-core/data/README.md`.
- ≥ 12 plies of the smoke-test PGN flagged as book.
- `manifest.opening_book_sha256` reflects the new value (verify by running an audit and inspecting the `manifest.json` written under `~/.cleanmatch/runs/<id>/`).

---

## 3. Add a corpus fixture and provenance (US3 — per-fixture)

```bash
# Example: adding a verified-clean OTB game from Tata Steel 2024 R3 G7.
FIXTURE_NAME="2024-tata-steel-r3-game7"

# 1. Place the PGN
mkdir -p tests/fixtures/corpora/clean
cp /path/to/source.pgn tests/fixtures/corpora/clean/${FIXTURE_NAME}.pgn

# 2. Write the provenance sibling
cat > tests/fixtures/corpora/clean/${FIXTURE_NAME}.provenance.json <<EOF
{
  "source": "https://www.tatasteelchess.com/games/2024/round-3",
  "retrieved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "label": "clean",
  "label_confidence": "high",
  "notes": "OTB game from official tournament broadcast; arbiter-monitored throughout."
}
EOF

# 3. Validate the provenance schema
uv run python -c "
import json, jsonschema
schema = json.load(open('specs/005-scoring-v2-phase2/contracts/provenance.schema.json'))
data = json.load(open('tests/fixtures/corpora/clean/${FIXTURE_NAME}.provenance.json'))
jsonschema.validate(data, schema)
print('OK')
"
```

For **engine-assisted** fixtures, swap the directory and ensure `notes` acknowledges the Lichess-classifier circularity risk per FR-005.

---

## 4. Run the FPR gate locally (US3)

```bash
# Cold cache (first run; takes up to 30 min depending on corpus size and engine speed)
uv run pytest tests/fixtures/corpora/test_fpr_gate.py -v

# Warm cache (after first run; should complete in seconds-to-minutes)
uv run pytest tests/fixtures/corpora/test_fpr_gate.py -v

# Inspect the diagnostic report
cat tests/fixtures/corpora/fpr_gate_report.json | jq .
```

If the gate fails, the report identifies offending fixtures. Per FR-010, do NOT relax thresholds — fix the algorithm in Phase 3 or remove a fixture with a corrected `.provenance.json` if it was mislabeled.

---

## 5. Verify the `AuditRun.manifest` envelope (US4)

```bash
# Run any audit
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/audit.json

# Confirm manifest is present in the JSON envelope (NOT just on disk)
jq '.manifest.rating_baselines_sha256, .manifest.signal_versions["acpl-analysis"]' /tmp/audit.json
# Expected: a 64-char hex string and a semver like "1.0.0"
```

If either is `null`, the `_build_run` attachment is broken — check that `AuditRun(... , manifest=manifest)` is wired correctly in `packages/analysis-core/src/analysis_core/pipeline/run.py`.

---

## End-to-end smoke

After all four tasks are done:

```bash
# 1. CI dry-run
uv run pytest -q packages/heuristics/tests packages/analysis-core/tests apps/cli/tests
uv run pytest -q tests/fixtures/corpora/test_fpr_gate.py

# 2. Re-run smoke-test audit and compare manifest sha256s
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/audit_v2_post_phase2.json
jq '.manifest | {rating_baselines_sha256, opening_book_sha256, signal_versions}' /tmp/audit_v2_post_phase2.json
```

Both sha256s should now reflect the **real** artifacts (not the stub-era zero or `0`-prefixed values). If you have a saved pre-Phase-2 audit JSON, the score values shift somewhat (deltas to be documented in `CHANGELOG.md` v2.0.0 entry per FR-009).
