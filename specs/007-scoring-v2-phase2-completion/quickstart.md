# Quickstart — Feature 007

One-command recipes per phase. All paths repo-relative; assume `uv` installed and workspace synced.

## §1 — Pre-flight (~5 min)

```bash
# Verify dump present + capture sha256
mkdir -p /tmp/baselines-007
sha256sum lichess_db_standard_rated_2026-04.pgn.zst | tee /tmp/baselines-007/notes.txt

# Verify SF16 image (podman is the canonical runtime on this maintainer
# machine; `docker` works identically if installed).
podman run --rm cleanmatch-stockfish:sf16 <<< 'quit' | head -1
#  must include "Stockfish 16"

# Verify zstd installed
zstd --version | head -1
```

## §2 — Pre-build audit snapshot (~30 s)

```bash
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/pre_007.json
jq '.score.score, .manifest.rating_baselines_sha256' /tmp/pre_007.json
```

## §3 — Real baselines build (~6 hr wall-clock — runs in background)

```bash
uv run python packages/heuristics/scripts/build_baselines.py \
  --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst \
  --stockfish-cmd "podman run --rm -i cleanmatch-stockfish:sf16" \
  --workers 6 --depth 12 --seed 0 --per-bucket-sample 5000 \
  --output packages/heuristics/data/rating_baselines.json
```

On Phase-2 abort (laptop sleep, OOM): re-run with same command + `--resume-from /tmp/baselines-007/`.

## §4 — Verify baselines (~10 s)

```bash
# No bucket below FR-001 floor
jq '.buckets[] | select(.sample_size < 1000)' packages/heuristics/data/rating_baselines.json
#  must print nothing

# Schema validation
uv run python -c "
import json, jsonschema
schema = json.load(open('specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json'))
data   = json.load(open('packages/heuristics/data/rating_baselines.json'))
jsonschema.validate(data, schema)
print('schema OK')
"

# New sha256
sha256sum packages/heuristics/data/rating_baselines.json
```

## §5 — Post-build delta capture (~30 s)

```bash
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/post_007.json
diff <(jq -S .manifest /tmp/pre_007.json) <(jq -S .manifest /tmp/post_007.json)
#  manifest diff must show rating_baselines_sha256 + manifest_sha256 changed
jq '.score.score' /tmp/pre_007.json /tmp/post_007.json
#  delta absolute value must be ≥ 0.005 per SC-005
```

## §6 — Engine-assisted corpus (~1 day manual sourcing)

Per disclosed Lichess banned-account ID:
```bash
curl -fS \
  -H "Accept: application/x-chess-pgn" \
  "https://lichess.org/api/games/user/<id>?max=5&tags=true" \
  > tests/fixtures/corpora/engine_assisted/<id>.pgn

# Provenance sibling
cat > tests/fixtures/corpora/engine_assisted/<id>.provenance.json <<JSON
{
  "source": "https://lichess.org/@/<id> (archive.org/<announcement-snapshot>)",
  "retrieved_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "label": "engine_assisted",
  "label_confidence": "high",
  "notes": "Lichess flagged-account game; label confidence reflects Lichess's own classifier — see spec.md FR-005 circularity edge case."
}
JSON
```

Validate all siblings:
```bash
uv run pytest tests/fpr_gate/test_provenance.py -v
```

## §7 — FPR-gate (~30 min cold cache, ~5 min warm)

```bash
uv run pytest tests/fpr_gate/test_fpr_gate.py -v -m fpr_gate --no-cov
cat tests/fixtures/corpora/fpr_gate_report.json | jq '.fpr, .tpr, .fpr_ci_95, .tpr_ci_95'
#  must show fpr ≤ 0.02, tpr ≥ 0.80
```

If FPR > 2% OR TPR < 80%: STOP. Do NOT relax the gate (FR-010). Escalate as Feature 008.

## §8 — Regression smoke (~10 min)

```bash
git checkout -b 007-regression-smoke-DELETEME
# Edit packages/heuristics/src/heuristics/scoring/aggregator.py: bias score by +0.3
git commit -am "test: regression bias for CI smoke (DELETE)"
git push -u origin 007-regression-smoke-DELETEME
gh pr create --draft --title "REGRESSION SMOKE — DELETE" --body "verify CI scoring gate"
gh pr edit --add-label scoring
#  Wait for CI; confirm fpr_gate job FAILS; screenshot the failure diagnostic.
gh pr close <num> --delete-branch
```

## §9 — Determinism (~1 min)

```bash
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/det1.json
uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/det2.json
diff <(jq -S .manifest /tmp/det1.json) <(jq -S .manifest /tmp/det2.json)
#  diff must be empty
```

## §10 — Pre-PR checks (~5 min)

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict packages/{heuristics,analysis-core,shared-types}/src
uv run pytest --cov --cov-fail-under=85
```

## §11 — Open PR

```bash
git push -u origin 007-scoring-v2-phase2-completion
gh pr create --title "feat(scoring): close feature 005 deferred work — real baselines + corpus + gate" \
  --body "..." \
  --label scoring
```
