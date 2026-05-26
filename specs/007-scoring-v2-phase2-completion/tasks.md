# Tasks — Feature 007 (Scoring v2 Phase 2 Completion)

**Input**: spec.md + plan.md + research.md (decisions D1–D8 referenced as R1–R8)

**Prerequisites**:
- Local archive `./lichess_db_standard_rated_2026-04.pgn.zst` (28 GB) present
- Docker available on maintainer machine (for SF16 image)
- Stockfish-16 reachable either via Docker or `shutil.which("stockfish")`
- `uv` installed; workspace synced

**Tests statement** (Principle II): every code path in `build_buckets_real` is covered by a `StaticAnalyzer`-injection unit test. No real Stockfish in CI. `pytest --cov --cov-fail-under=85` is a Phase 6 gate.

**Organization rules**:
- `[P]` = parallel-safe with other `[P]` tasks
- `[USx]` = user-story tag (USA = real baselines, USB = engine corpus, USC = FPR-gate, USD = docs)
- `⇐ TNNN` = depends on the named task
- `[X]` once completed

---

## Phase 0 — Setup

- [ ] **T001** Branch + spec scaffold. `git checkout -b 007-scoring-v2-phase2-completion`. Create `specs/007-scoring-v2-phase2-completion/{spec.md, plan.md, tasks.md, quickstart.md, research.md, HANDOFF.md, contracts/.gitkeep, checklists/requirements.md}`. (DONE — this is the file being written.)

## Phase 1 — Foundational

- [ ] **T002** [P] Add `zstandard >= 0.22, < 1.0` to `packages/heuristics/pyproject.toml` `[project.optional-dependencies].dev`. Run `uv sync`. Document the new dep in `pyproject.toml` with a short comment ("streaming PGN ingest from .zst archives").
- [ ] **T003** [P] Build SF16 Docker image. `docker build -t cleanmatch-stockfish:sf16 -f infra/docker/stockfish.Dockerfile .`. Verify with `docker run --rm cleanmatch-stockfish:sf16 stockfish` (greeting line includes "Stockfish 16"). Record image sha256 + Stockfish binary sha256 in scratch notes (feeds `source_dataset` label in T004 + `data/README.md` in T018).

## Phase 2 — User Story A: real baselines (P1)

> **Note (T007 v2, 2026-05-26)**: T004 originally specified a pickle-checkpoint
> two-phase architecture. After the v1 run lost 30000 in-RAM analyses to a
> podman-engine handle leak in `ProcessPoolExecutor.shutdown`, the
> architecture was migrated to Postgres-backed persistence. Tasks T007a-T007e
> below replace the previous T004 + T007 with the new flow; the old `[X]`
> tasks remain marked complete because their underlying outputs (zstd dep,
> SF16 image, sample reservoir code, schema validation) carried over.

- [ ] **T004** [USA, ⇐ T002] Rewrite `build_buckets_real()` in `packages/heuristics/scripts/build_baselines.py`. Implements:
  - `DEFAULT_MONTH = "2026-04"` (R1)
  - CLI flags: `--input-zst PATH` (default `./lichess_db_standard_rated_2026-04.pgn.zst`), `--stockfish-cmd CMD` (default Docker per R5, fallback `shutil.which("stockfish")`), `--workers INT` (default 6), `--per-bucket-sample INT` (default 5000), `--depth INT` (default 12), `--resume-from CHECKPOINT_DIR` (default `/tmp/baselines-007/`)
  - `_stream_filtered_games(zst_path, seed) -> Iterator[bytes]` per R2: spawns `zstd -d -c <path>` subprocess; `chess.pgn.read_game` loop; applies the FR-003 filter (Elo ∈ [600, 3500] both, TC ∈ {RAPID, CLASSICAL}, ply ≥ 20)
  - Deterministic reservoir sampling (Algorithm L) keyed on `random.Random(seed)` per R6
  - Two-phase architecture per R3: Phase 1 writes `*.sample.pgn` checkpoints; Phase 2 runs analysis with restartability via `--resume-from`
  - `_analyze_sample(games, stockfish_cmd, depth, workers) -> per-bucket stats`: per-position SF16 depth-12; computes top-1 / weighted-top-1 / ACPL; aggregates to mean + population stdev per bucket
  - `build_buckets_real(...)` returns 6 measured buckets + `rating-unknown` as elementwise median per R4
  - `source_dataset = f"lichess_db_standard_rated_2026-04 (sha256={archive_sha256})"`

### Phase 2b — T007 v2: Postgres-backed re-implementation (2026-05-26)

- [X] **T007a** Rebase branch `007-scoring-v2-phase2-completion` onto `main` to absorb feature 008's DB infrastructure (`analysis_core.db.session`, `analysis_core.db.models`, alembic scaffold). Resolve `.gitignore` + `README.md` conflicts. Start podman compose Postgres. Verify with `\dt`.
- [X] **T007b** [⇐ T007a] Migration `packages/analysis-core/migrations/versions/0002_baseline_persistence.py` adds 4 tables (`baseline_runs`, `pgn_corpus`, `baseline_samples`, `baseline_analyses`), trigger function `fn_mark_sample_analysed`, trigger `trg_mark_sample_analysed`, view `baseline_buckets`. Extend `analysis_core.db.models` with 4 new ORM classes mirroring the migration. Verify `alembic upgrade head` + `alembic downgrade -1` round-trip is clean.
- [X] **T007c** [⇐ T007b] Repository layer at `packages/analysis-core/src/analysis_core/db/baseline_store.py`: `create_run()`, `flush_reservoir()` (chunked at 5000 rows per psycopg's 65535-param cap), `claim_sample()` (`SELECT FOR UPDATE SKIP LOCKED` + 15-min stale-claim recovery), `persist_analysis()`, `mark_phase1_done()`, `mark_run_completed()`, `mark_run_failed()`, `fetch_bucket_aggregates()`, `compute_rating_unknown_row()`. Plus 16 unit tests at `packages/analysis-core/tests/test_baseline_store.py` covering create / upsert / claim concurrency / stale recovery / trigger / aggregates / lifecycle.
- [X] **T007d** [⇐ T007c] Refactor `packages/heuristics/scripts/build_baselines.py`:
  - Drop `write_checkpoints` / `read_checkpoints` / `_safe_label` (pickle path)
  - Drop `_worker_analyse` / `analyse_samples_parallel` / `analyse_samples` (RAM-only paths)
  - Add `_stream_with_db_flush()` — Phase 1 with periodic flush every `--flush-every` games (default 100k)
  - Add `_worker_claim_loop()` — workers loop claim→analyse→persist until no more pending samples
  - Add `analyse_samples_against_db()` — pool orchestration + periodic progress polling
  - New CLI flag `--run-id <uuid>` for resume (skips Phase 1)
  - New CLI flag `--flush-every <int>` to tune Phase-1 flush cadence
  - Add `analysis-core` to `packages/heuristics/pyproject.toml` runtime deps
- [ ] **T007e** [⇐ T007d] Execute real build on 2026-04 Lichess dump. ~21 min Phase 1 + ~5.5 h Phase 2. Verify output JSON validates against schema + spot-check values against the previous stub. Capture run_id in scratch notes for the dump recipe (Phase F).
- [ ] **T005** [USA, ⇐ T004] Unit tests at `packages/heuristics/tests/test_build_baselines.py`. Inject a `StaticAnalyzer` protocol so no real Stockfish needed. Coverage:
  - `_stream_filtered_games` against a 3-game in-memory zst fixture (one passing all filters, two failing different filters)
  - Reservoir determinism (same seed + same input → identical sample list)
  - Bucketing edges (`min(1200, 1500) → "≤1200"`; `min=2401 → "2401+"`; `min=599` rejected)
  - `_analyze_sample` end-to-end with `StaticAnalyzer` returning known top-1 / ACPL
  - `build_buckets_real` schema validation via `jsonschema.validate` against `specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json`
  - `rating-unknown` bucket is the elementwise median of the 6 rated buckets
- [ ] **T006** [USA, ⇐ T004] Pre-build audit snapshot:
  ```bash
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/pre_007.json
  jq '.score.score, .manifest.rating_baselines_sha256' /tmp/pre_007.json
  ```
  Record both values in scratch notes for delta computation in T009.
- [ ] **T007** [USA, ⇐ T005] Run real build (maintainer machine, ~6 hr wall-clock; background-runnable):
  ```bash
  uv run python packages/heuristics/scripts/build_baselines.py \
    --input-zst ./lichess_db_standard_rated_2026-04.pgn.zst \
    --stockfish-cmd "docker run --rm -i cleanmatch-stockfish:sf16" \
    --workers 6 --depth 12 --seed 0 --per-bucket-sample 5000 \
    --output packages/heuristics/data/rating_baselines.json
  ```
  On Phase-2 abort: re-run with the same command + `--resume-from /tmp/baselines-007/`.
- [ ] **T008** [USA, ⇐ T007] Verify output:
  - `jq '.buckets[] | select(.sample_size < 1000)' packages/heuristics/data/rating_baselines.json` must return empty
  - Schema validates via `python -c "import json, jsonschema; jsonschema.validate(json.load(open('packages/heuristics/data/rating_baselines.json')), json.load(open('specs/004-scoring-v2-phase1/contracts/rating_baselines.schema.json')))"`
  - Capture new file sha256: `sha256sum packages/heuristics/data/rating_baselines.json | tee -a /tmp/baselines-007/notes.txt`
- [ ] **T009** [USA, ⇐ T007] Post-build audit snapshot + delta:
  ```bash
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/post_007.json
  diff <(jq -S .manifest /tmp/pre_007.json) <(jq -S .manifest /tmp/post_007.json)
  jq '.score.score' /tmp/pre_007.json /tmp/post_007.json
  ```
  Manifest diff must show `rating_baselines_sha256` change; score delta ≥ 0.005 absolute per SC-005.

## Phase 3 — User Story B: engine-assisted corpus (P1)

- [ ] **T010** [USB] Source 25 PGNs into `tests/fixtures/corpora/engine_assisted/<lichess-id>.pgn`. Strategy per R7:
  - Search `lichess.org/forum/lichess-feedback` + r/chess archive for ban-announcement threads ("closed for using outside assistance", "ToS violation: assistance")
  - For each disclosed account ID, `curl "https://lichess.org/api/games/user/<id>?max=5&tags=true" -H "Accept: application/x-chess-pgn" > tests/fixtures/corpora/engine_assisted/<id>.pgn`
  - Skip purged accounts (HTTP 404)
  - Aim for 25; 20 is the FR-005 floor with a 5-fixture buffer
- [ ] **T011** [USB, ⇐ T010] Per-PGN `.provenance.json` siblings per `tests/fpr_gate/contracts/provenance.schema.json`. Each contains:
  - `source`: `"https://lichess.org/@/<id>"` + archive.org snapshot of ban announcement
  - `retrieved_at`: ISO-8601 UTC
  - `label`: `"engine_assisted"`
  - `label_confidence`: `"high"`
  - `notes`: exact verbatim sentence — *"Lichess flagged-account game; label confidence reflects Lichess's own classifier — see spec.md FR-005 circularity edge case."*
- [ ] **T012** [USB, ⇐ T011] `uv run pytest tests/fpr_gate/test_provenance.py -v`. All 25 sibling files validate.

## Phase 4 — User Story C: FPR-gate validation (P1)

- [ ] **T013** [USC, ⇐ T009 + T012] Cold-cache gate run:
  ```bash
  uv run pytest tests/fpr_gate/test_fpr_gate.py -v -m fpr_gate --no-cov
  cat tests/fixtures/corpora/fpr_gate_report.json | jq '.fpr, .tpr, .fpr_ci_95, .tpr_ci_95'
  ```
  Up to 30 minutes wall-clock. If `FPR > 2%` OR `TPR < 80%`: **STOP**, log to scratch notes, escalate as Feature 008 per FR-010. **Do NOT relax the gate.**
- [ ] **T014** [USC, ⇐ T013] Regression-PR smoke (T025 of 005):
  ```bash
  git checkout -b 007-regression-smoke-DELETEME
  # Edit packages/heuristics/src/heuristics/scoring/aggregator.py: bias score by +0.3
  git commit -am "test: regression bias for CI smoke (DELETE)"
  git push -u origin 007-regression-smoke-DELETEME
  gh pr create --draft --title "REGRESSION SMOKE — DELETE" --body "verify CI scoring gate"
  gh pr edit --add-label scoring
  ```
  Confirm CI `fpr_gate` job fails with the diagnostic from `fpr_gate.contract.md §Output`. Screenshot the failure. Close + delete the branch and PR.
- [ ] **T015** [USC, ⇐ T013] Determinism re-run:
  ```bash
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/det1.json
  uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/det2.json
  diff <(jq -S .manifest /tmp/det1.json) <(jq -S .manifest /tmp/det2.json)
  ```
  Diff must be empty. Embed both `run.id` UUIDs in the PR description.

## Phase 5 — User Story D: documentation + CHANGELOG (P2)

- [ ] **T016** [USD, ⇐ T009 + T013] Edit `CHANGELOG.md`:
  - Move all four bullets from `### Pending (Feature 005 — to land before v2.0.0 promotion)` (lines 81-93 today) into the `### Added — Feature 005 (Scoring v2 Phase 2)` block above
  - Substitute placeholders with measured values:
    - `FPR = X.X% (n/50) [95% CI Y.Y%–Z.Z%]`
    - `TPR = X.X% (n/25) [95% CI Y.Y%–Z.Z%]`
    - `score delta on audit_v2_smoke.pgn: pre=A.AAA → post=B.BBB (Δ=C.CCC)`
    - new `rating_baselines.json` sha256
  - Replace `## [Unreleased]` with `## [2.1.0] — <today>`
- [ ] **T017** [USD] `packages/heuristics/CHANGELOG.md` — single-line entry: "rating_baselines.json regenerated from Lichess 2026-04 (real data, seed=0, depth=12, per-bucket n≥1000)".
- [ ] **T018** [USD] Create `packages/heuristics/data/README.md`: source URL, sha256 of local `.zst`, retrieval date, exact build command + seed, Stockfish binary sha256 (from T003).
- [ ] **T019** [USD] Update `specs/005-scoring-v2-phase2/HANDOFF.md`:
  - Strike T007-T010 / Block B-2 / T023 / T025 / T030 blocks
  - Add link to feature 007 PR URL
- [ ] **T020** [USD] Update `specs/005-scoring-v2-phase2/tasks.md`: mark `T007, T008, T009, T010, T021, T022, T023, T025, T030, T038` as `[X]`.

## Phase 6 — Polish + PR

- [ ] **T021** `uv run ruff check . && uv run ruff format --check .`
- [ ] **T022** `uv run mypy --strict packages/{heuristics,analysis-core,shared-types}/src`
- [ ] **T023** `uv run pytest --cov --cov-fail-under=85` (new `build_buckets_real` paths covered via `StaticAnalyzer` injection from T005)
- [ ] **T024** Quickstart walkthrough on fresh checkout (T038-of-005 acceptance). Document any deviations in the PR description.
- [ ] **T025** Final Constitution Principles I–IV signoff in PR description. Open PR with `scoring` label.

---

## Checkpoints

After Phase 2: USA functional — `rating_baselines.json` shipped with real data, manifest stamps verified. T009 delta proves observability.

After Phase 4: USC complete — FPR/TPR gate validated against real corpus. If FAIL, ESCALATE to Feature 008 per FR-010.

After Phase 6: PR ready. CI green on `test`, `fpr_gate`, `design_system_audits`. `[2.1.0]` published.
