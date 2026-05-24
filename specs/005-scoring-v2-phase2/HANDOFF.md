# Feature 005 — Hand-off: human-action gates

Branch `005-scoring-v2-phase2` ships code, tests, CI workflow, CHANGELOGs, the real opening book, and 50 clean corpus fixtures. The remaining tasks require maintainer-machine resources (29 GB Lichess dataset, Stockfish runtime, manual sourcing of publicly-disclosed cheat cases). Maintainer action items below, grouped by dependency.

---

## Status (2026-05-24)

- **Tasks complete**: 29/39 marked `[X]` in `tasks.md`.
- **Pipeline green**: `uv run pytest --cov` → 421 passed, 3 skipped, **coverage ≥ 85%**.
- **Lint/type clean**: `uv run ruff check .` + `uv run ruff format --check .` + `uv run mypy` all pass.
- **Real opening book installed**: 6.5 MB at `packages/analysis-core/data/opening_book.bin`,
  sha256 `dd0c9b50f75274b421ee9bfa12b45920b38124c9e2c7768f1179d130357c4532`,
  derived from Lichess broadcast 2025-02/03/04 archives (60k OTB games).
- **50 clean corpus fixtures** under `tests/fixtures/corpora/clean/` with
  matching `.provenance.json` siblings.
- **CI workflow added**: `.github/workflows/ci.yml` declares the `fpr_gate` job.
  Currently SKIPS gracefully because `engine_assisted/` corpus is empty.

---

## Hand-off blocks

### Block A — Real production artifacts (US1 + US2)

These two tasks block the smoke-test score delta needed for `CHANGELOG.md` v2.0.0 entry numbers.

#### T007 + T008 + T009 + T010 — Real Lichess baselines

Follow `quickstart.md §1`. Summary:

```bash
curl -L -o /tmp/lichess_2026-04.pgn.zst \
  https://database.lichess.org/standard/lichess_db_standard_rated_2026-04.pgn.zst
zstd -d /tmp/lichess_2026-04.pgn.zst -o /tmp/lichess_2026-04.pgn

uv run python packages/heuristics/scripts/build_baselines.py \
  --input /tmp/lichess_2026-04.pgn \
  --output packages/heuristics/data/rating_baselines.json \
  --source-label "lichess_db_standard_rated_2026-04"

# Verify
uv run pytest packages/heuristics/tests/test_real_baselines_smoke.py
```

- **Estimated time**: ~30-90 min build + multi-GB download.
- **Fallback**: if 2026-04 is unreachable, use 2026-03 (or earlier complete month) per FR-001.
- **T010 delta capture**: BEFORE running T008, snapshot a smoke-test audit:
  `cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/pre.json`.
  After T008, repeat → `/tmp/post.json`. Diff goes into `CHANGELOG.md`.

#### T011 + T012 + T013 — Real `gm2600.bin`

Follow `quickstart.md §2`:

```bash
curl -L -o /tmp/gm2600.bin \
  https://github.com/michaelb/Sayuri-chess-bot/raw/main/books/gm2600.bin
sha256sum /tmp/gm2600.bin   # record this value

cp /tmp/gm2600.bin packages/analysis-core/data/opening_book.bin
# Edit packages/analysis-core/data/README.md per data-model.md §4.

uv run pytest packages/analysis-core/tests/test_real_book_coverage.py
```

- **Estimated time**: < 5 min.
- **Failure mode**: if upstream sha256 doesn't match any documented canonical value, find an alternate mirror with a matching sha256 or escalate. Do NOT commit a tampered file.

---

### Block B — Labeled corpus (US3 — T019 to T022)

This is the largest human-action block. Source per `research.md` R3 + R4. Follow `quickstart.md §3` for the per-fixture recipe.

- **T019 + T020 — Clean corpus (≥ 50 PGNs)**:
  - ~30 OTB tournament broadcast PGNs (Tata Steel, Candidates, Chess.com Tour, lichess.org/broadcasts).
  - ~15 streamed top-100 player games.
  - ~5 pre-2010 GM archive games (low-priority fallback only if (1)+(2) don't reach 50).
  - Each PGN MUST have a sibling `.provenance.json` matching `contracts/provenance.schema.json`. `label = "clean"`, `label_confidence = "high"` or `"medium"`.

- **T021 + T022 — Engine-assisted corpus (≥ 20 PGNs)**:
  - Source: Lichess closed/flagged accounts whose closure reason is publicly visible (`closed: true` with `mark: cheat` flag).
  - `label = "engine_assisted"`, `label_confidence = "high"`.
  - **MANDATORY** in `notes`: acknowledge the Lichess-classifier circularity risk per `spec.md` Edge Cases.

- **Estimated time**: 4-8 hours of careful sourcing + provenance writing.

---

### Block C — Gate validation + CI smoke (T023, T025)

After Blocks A and B land:

- **T023**: `uv run pytest tests/fpr_gate/test_fpr_gate.py -v -m fpr_gate`. Cold-cache run takes up to 30 min. If FPR > 2% or TPR < 80% → algorithm tuning is Phase 3, NOT threshold relaxation (FR-010).
- **T025**: Create a throwaway local branch with `aggregator.py` regression (e.g. `score = min(1.0, score + 0.3)`). Push as draft PR. Confirm CI `fpr_gate` job fails with the documented diagnostic. Delete the draft.

---

### Block D — Final verification (T030, T038)

- **T030**: After Block A+B+C complete, run:
  ```bash
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/run1.json
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/run2.json
  diff <(jq -S '.manifest' /tmp/run1.json) <(jq -S '.manifest' /tmp/run2.json)
  ```
  Empty diff required (SC-007 determinism). Embed both run.id values in the PR description.

- **T038**: Walk through `specs/005-scoring-v2-phase2/quickstart.md` step by step on a fresh checkout. Document deviations in PR description.

---

## Branch-protection note (F5)

The `fpr_gate` CI job runs path-filtered, but making it **required for merge** is a branch-protection setting on `main` configured by the maintainer in GitHub UI → Settings → Branches → `main` → "Require status checks to pass" → add `fpr_gate`. This is NOT done by the workflow file alone.

---

## Maintainer checklist before merging this PR

- [ ] Block A complete (real baselines + book committed; sha256s recorded in `packages/analysis-core/data/README.md` and `rating_baselines.json`).
- [ ] Block B complete (50+ clean PGNs + 20+ engine-assisted PGNs with provenance siblings).
- [ ] Block C T023 green (FPR ≤ 2%, TPR ≥ 80%).
- [ ] Block C T025 demonstrated (regression PR blocked by CI).
- [ ] Block D T030 verified (determinism).
- [ ] Block D T038 walked through cleanly.
- [ ] `CHANGELOG.md` updated with real FPR/TPR numbers + smoke-test score deltas (the "Pending" stanza in v2.0.0 entry is replaced with measured values).
- [ ] `tasks.md` — remaining 15 tasks marked `[X]`.
- [ ] Branch protection on `main` updated to require `fpr_gate` status check.
