---
description: "Task list for feature 001-fairplay-analysis (Probabilistic Fair Play Analysis Platform)"
---

# Tasks: Probabilistic Fair Play Analysis Platform

**Input**: Design documents from `/specs/001-fairplay-analysis/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: REQUIRED for this feature. Constitution Principle II
(NON-NEGOTIABLE) mandates unit tests for every signal computation, every
scoring aggregation, and every report path, plus integration tests covering
the end-to-end CLI flow on at least one known-clean and one known-suspect
fixture. Coverage gate: 85% line / 80% branch on `packages/*/src/`.
Red → green discipline applies to all signal modules.

**Organization**: Tasks are grouped by user story (US1…US4 from `spec.md`)
to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on
  incomplete tasks).
- **[Story]**: User story tag (US1, US2, US3, US4). Setup, Foundational,
  and Polish phases carry no story tag.

## Path Conventions

Monorepo (Python uv workspace) — see `plan.md` Project Structure:

- CLI entry point: `apps/cli/`
- Reusable libs: `packages/{analysis-core,heuristics,report-engine,shared-types}`
- Fixtures: `tests/fixtures/`
- Cross-package e2e: `tests/e2e/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Bootstrap the monorepo, tooling, and CI scaffolding.

- [ ] T001 Create the monorepo skeleton at the repo root: `apps/{cli,api,frontend}/`, `packages/{analysis-core,heuristics,report-engine,shared-types}/`, `infra/{docker,compose}/`, `tests/{fixtures,e2e}/` (empty `__init__.py` / placeholder files where needed)
- [ ] T002 [P] Create root `pyproject.toml` declaring the uv workspace and the Python 3.11 requirement, listing all `apps/*` and `packages/*` as workspace members
- [ ] T003 [P] Add per-package `pyproject.toml` files under `apps/cli/`, `packages/analysis-core/`, `packages/heuristics/`, `packages/report-engine/`, `packages/shared-types/` with name, version 0.1.0, and Python 3.11 requirement
- [ ] T004 [P] Configure `ruff` (lint + format) at root `pyproject.toml` `[tool.ruff]`, enabling `E,F,W,I,N,UP,B,S,A,ARG,RUF` and excluding `tests/fixtures/`
- [ ] T005 [P] Configure `mypy --strict` at root `pyproject.toml` `[tool.mypy]`, targeting `packages/*/src/` and `apps/cli/src/`
- [ ] T006 [P] Configure `pytest` + `pytest-cov` + `pytest-benchmark` at root `pyproject.toml` `[tool.pytest.ini_options]`, including `markers = ["slow", "benchmark", "e2e"]`, `addopts = "--strict-markers --cov-fail-under=85"`
- [ ] T007 [P] Create `.github/workflows/ci.yml` running on push/PR: `uv sync` → `uv run ruff check` → `uv run ruff format --check` → `uv run mypy` → `uv run pytest`
- [ ] T008 [P] Add `.editorconfig`, `.gitignore` (Python, uv, `.cleanmatch/`, `dist/`, `*.pdf` build artefacts), and update root `README.md` pointing at `specs/001-fairplay-analysis/quickstart.md`

**Checkpoint**: `uv sync && uv run pytest` (no tests yet) and `uv run mypy` both succeed on an empty workspace.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before any user story can be implemented.

⚠️ **CRITICAL**: No user story work can begin until this phase is complete.

### Shared types (data-model.md → `packages/shared-types/`)

- [ ] T009 [P] Create `packages/shared-types/src/shared_types/__init__.py` exporting all schemas listed below
- [ ] T010 [P] Implement `Game`, `PlayerRef`, `Move`, `CandidateMove`, `Position`, `ComplexityScore` Pydantic v2 models in `packages/shared-types/src/shared_types/game.py`
- [ ] T011 [P] Implement `Segment`, `HeuristicVersion`, `SignalContribution`, `SignalAggregate` models in `packages/shared-types/src/shared_types/signal.py`
- [ ] T012 [P] Implement `SuspicionScore` with risk-level enum bound to the locked thresholds (low <0.35, medium [0.35,0.70), high ≥0.70) in `packages/shared-types/src/shared_types/score.py`
- [ ] T013 [P] Implement `AuditRun`, `RunError`, `EngineFingerprint`, `AccountProfile`, `CrossGamePattern` models in `packages/shared-types/src/shared_types/audit_run.py`
- [ ] T014 [P] Implement `Report`, `Narrative`, `FlaggedSegment`, `ReproducibilityManifest`, `HostInfo` models in `packages/shared-types/src/shared_types/report.py`
- [ ] T015 Add unit tests covering validation rules (variant must be "standard", ply_count ≥ 10 for scoring eligibility, threshold→risk-level mapping) in `packages/shared-types/tests/`

### Engine + manifest + cache (analysis-core foundation)

- [ ] T016 [P] Implement `packages/analysis-core/src/analysis_core/manifest.py` — builds `ReproducibilityManifest` from engine fingerprint, heuristic registry snapshot, library versions, input PGN SHA256, opening-book SHA256, host info
- [ ] T017 [P] Implement `packages/analysis-core/src/analysis_core/engine/uci.py` — thin wrapper over `python-chess` `engine.SimpleEngine` that pins UCI options (`Threads=1, Hash=256, MultiPV=5, UseNNUE=true`) and rejects mutations after initialisation
- [ ] T018 Implement `packages/analysis-core/src/analysis_core/engine/stockfish_pool.py` — multiprocessing pool of UCI workers, deterministic settings, graceful shutdown; depends on T017
- [ ] T019 [P] Implement `packages/analysis-core/src/analysis_core/pipeline/cache.py` — deterministic cache keyed by manifest hash, persists under `${CLEANMATCH_HOME:-~/.cleanmatch}/runs/<run-id>/`
- [ ] T020 [P] Add unit tests in `packages/analysis-core/tests/` covering: manifest determinism (same inputs → same SHA), engine UCI option pinning, cache hit/miss + bypass via `--no-cache`

### Heuristics registry + scoring scaffold

- [ ] T021 Implement `packages/heuristics/src/heuristics/registry.py` — versioned signal registry returning `tuple[(name, version, callable)]`; signal modules register on import
- [ ] T022 [P] Implement `packages/heuristics/src/heuristics/scoring/thresholds.py` exposing the locked risk thresholds (low <0.35, medium [0.35,0.70), high ≥0.70) and version stamp; manifest pulls thresholds + version from here
- [ ] T023 [P] Add unit tests in `packages/heuristics/tests/test_registry.py` covering: registration, version retrieval, frozen-tuple immutability, threshold→risk-level pure function

### Opening-book infrastructure (Principle 6)

- [ ] T024 [P] Implement `packages/analysis-core/src/analysis_core/ingest/opening_book.py` — Polyglot book loader (Lichess Masters book, ≥2400 Elo, depth 20 plies) with SHA256-pinned identity; exposes `is_book_ply(position) -> bool`
- [ ] T025 [P] Bundle the Lichess Masters Polyglot book at `packages/analysis-core/data/books/lichess-masters-2400-d20.bin` and record its SHA256 in `packages/analysis-core/data/books/manifest.json`
- [ ] T026 [P] Add unit tests for opening-book lookup against pinned fixtures in `packages/analysis-core/tests/test_opening_book.py`

### CLI scaffold + logging (Principle III)

- [ ] T027 [P] Implement `apps/cli/src/cleanmatch_cli/main.py` — `typer` app with `audit-game`, `audit-username`, `show`, `export` subcommand stubs that exit with `1` ("not implemented yet") so the CLI surface is testable from day one
- [ ] T028 [P] Implement `apps/cli/src/cleanmatch_cli/output/exit_codes.py` mapping `user_error → 1`, `upstream_error → 2`, `internal_error → 3` (matches contracts)
- [ ] T029 [P] Implement `apps/cli/src/cleanmatch_cli/output/logging.py` — `structlog` configuration with pretty (stderr) and JSON formatters, controlled by `--log-format` flag and `CLEANMATCH_LOG_FORMAT` / `CLEANMATCH_LOG_LEVEL` env vars
- [ ] T030 [P] Implement `apps/cli/src/cleanmatch_cli/output/renderers.py` — human and JSON renderers; the JSON renderer goes to stdout, human goes to stdout, logs always to stderr
- [ ] T031 [P] Add CLI contract tests under `apps/cli/tests/contract/` verifying flag grammar (`--output`, `--log-format`, `--log-level`, `--debug`), exit-code mapping, and stdout/stderr separation for each subcommand stub

### Test fixtures + forbidden-terms list

- [ ] T032 [P] Create `tests/fixtures/pgn/known-clean/` with at least 2 canonical PGNs (deterministic, redistributable) and `tests/fixtures/pgn/known-suspect/` with at least 2 canonical PGNs covering selective-assistance and full-engine examples (SC-002 dataset rules)
- [ ] T033 [P] Create `tests/fixtures/stockfish/<engine-sha>/<pgn-sha>/<ply>.json` snapshot directory layout plus a snapshot-replay engine adapter under `packages/analysis-core/src/analysis_core/engine/snapshot_engine.py` so unit tests can run without the Stockfish binary
- [ ] T034 [P] Create `tests/fixtures/forbidden-terms/en.txt` and `tests/fixtures/forbidden-terms/pt.txt` with per-entry `term\tcategory\tmatch_mode` (accusation | verdict | slur ; word_boundary | substring); seed with the SC-008 examples ("cheater", "trapaceiro", "guilty") plus an initial curated set
- [ ] T035 [P] Add a fixture-integrity test in `tests/e2e/test_fixtures.py` that parses every fixture PGN, asserts ply_count ≥ 10 and variant == standard, and validates the forbidden-terms files are well-formed TSV

**Checkpoint**: All foundational packages import cleanly; `uv run mypy` + `uv run ruff check` clean; foundational unit tests pass; CLI stubs print help and exit 1 on each subcommand.

---

## Phase 3: User Story 1 — Single-game probabilistic audit (Priority: P1) 🎯 MVP

**Goal**: User provides a PGN, the system returns a probabilistic suspicion score with a one-paragraph narrative.

**Independent Test**: `cleanmatch audit-game tests/fixtures/pgn/known-suspect/example.pgn --output json` returns a JSON document with `score`, `risk_level == "high"`, `dominant_signals`, and a flagged segment. The same command on `tests/fixtures/pgn/known-clean/` returns `risk_level == "low"`.

### Tests for User Story 1 (RED-first per constitution Principle II)

- [ ] T036 [P] [US1] Write failing unit tests for PGN ingestion (valid PGN parses; malformed header → typed error; non-standard variant → reject; ply_count < 10 → ineligible) in `packages/analysis-core/tests/test_pgn_loader.py`
- [ ] T037 [P] [US1] Write failing unit tests for per-position engine analysis using the snapshot engine adapter in `packages/analysis-core/tests/test_engine_analysis.py`
- [ ] T038 [P] [US1] Write failing unit tests for `ComplexityScore` computation (branching, volatility, density, ambiguity) on pinned positions in `packages/heuristics/tests/test_complexity_analysis.py`
- [ ] T039 [P] [US1] Write failing unit tests for tactical-position / only-move detection in `packages/heuristics/tests/test_tactical_detection.py`
- [ ] T040 [P] [US1] Write failing unit tests for segmentation (opening / middlegame / tactical / conversion / endgame + regime shift detection) in `packages/heuristics/tests/test_regime_shift.py`
- [ ] T041 [P] [US1] Write failing unit tests for engine_correlation signal (top-1 match, top-3 match, complexity-weighted correlation per Principle 7) in `packages/heuristics/tests/test_engine_correlation.py`
- [ ] T042 [P] [US1] Write failing unit tests for behavioral_patterns signal (bursts of precision, blunder suppression, alternation) in `packages/heuristics/tests/test_behavioral_patterns.py`
- [ ] T043 [P] [US1] Write failing unit tests for timing_analysis signal in `packages/heuristics/tests/test_timing_analysis.py`
- [ ] T044 [P] [US1] Write failing unit tests for score aggregation + bootstrap CI (N=1000) + threshold→risk-level mapping in `packages/heuristics/tests/test_scoring.py`
- [ ] T045 [P] [US1] Write failing CLI integration test `apps/cli/tests/integration/test_audit_game.py` that exercises the full pipeline against the known-clean and known-suspect fixtures and asserts the documented exit-code and JSON-shape contract from `contracts/cli-audit-game.md`
- [ ] T046 [P] [US1] Write failing determinism integration test `apps/cli/tests/integration/test_determinism.py` that runs `audit-game` twice on the same fixture and asserts bit-identical JSON output (FR-017, same architecture)

### Implementation for User Story 1

- [ ] T047 [US1] Implement PGN loader + canonicalisation (headers sorted, whitespace stripped) + SHA256 in `packages/analysis-core/src/analysis_core/ingest/pgn_loader.py` (turns T036 green)
- [ ] T048 [US1] Implement per-position engine analysis (top-N candidates via MultiPV, eval in cp / mate_in) in `packages/analysis-core/src/analysis_core/engine/analysis.py` (turns T037 green); depends on T018
- [ ] T049 [US1] Implement `packages/analysis-core/src/analysis_core/pipeline/segmentation.py` — phase boundaries + regime-shift detector (turns T040 green)
- [ ] T050 [P] [US1] Implement `packages/heuristics/src/heuristics/complexity_analysis/__init__.py` with `__signal_version__ = "0.1.0"` (turns T038 green)
- [ ] T051 [P] [US1] Implement `packages/heuristics/src/heuristics/tactical_detection/__init__.py` (turns T039 green)
- [ ] T052 [P] [US1] Implement `packages/heuristics/src/heuristics/engine_correlation/__init__.py` with top-1, top-3, and complexity-weighted match (turns T041 green); depends on T050
- [ ] T053 [P] [US1] Implement `packages/heuristics/src/heuristics/behavioral_patterns/__init__.py` (turns T042 green)
- [ ] T054 [P] [US1] Implement `packages/heuristics/src/heuristics/regime_shift/__init__.py` (turns T040 green for regime portion)
- [ ] T055 [P] [US1] Implement `packages/heuristics/src/heuristics/timing_analysis/__init__.py` (turns T043 green)
- [ ] T056 [US1] Implement `packages/heuristics/src/heuristics/scoring/__init__.py` — aggregator + bootstrap CI (N=1000) + risk classifier; book and forced-move plies excluded; depends on T021-T024, T050-T055 (turns T044 green)
- [ ] T057 [US1] Implement `packages/analysis-core/src/analysis_core/pipeline/run.py` — `AuditRun` orchestrator: ingest → engine pool → analysis → segmentation → registered signals → scoring → persist under `~/.cleanmatch/runs/<run-id>/`; depends on T016-T019, T047-T056
- [ ] T058 [US1] Implement `apps/cli/src/cleanmatch_cli/commands/audit_game.py` per `contracts/cli-audit-game.md`; depends on T027-T030, T057 (turns T045 and T046 green)
- [ ] T059 [US1] Implement plain-language move-level rationale strings for each signal (FR-012); strings live in each heuristic module's `narrative.py`
- [ ] T060 [US1] Run the full US1 test suite and confirm ≥85% line / ≥80% branch coverage on touched packages

**Checkpoint**: User Story 1 is fully functional. `cleanmatch audit-game` produces a deterministic, explainable result on the canonical fixtures.

---

## Phase 4: User Story 2 — Audit by chess.com username (Priority: P2)

**Goal**: User supplies a public chess.com username + count; the system fetches recent games, audits each, and emits an account profile.

**Independent Test**: `cleanmatch audit-username <pinned-test-account> --count 5 --output json` returns 5 per-game results plus an aggregated profile. The per-game results match what `audit-game` produces on the same fixtures.

### Tests for User Story 2

- [ ] T061 [P] [US2] Write failing unit tests for the chess.com archive index lookup, monthly fetch, and 429/5xx backoff (1/2/4/8/16 s, max 3 retries) in `packages/analysis-core/tests/test_chesscom_client.py` (use `pytest-httpx` to mock responses)
- [ ] T062 [P] [US2] Write failing unit tests for the time-control filter and "fewer games than requested" handling in the same file
- [ ] T063 [P] [US2] Write failing unit tests for `AccountProfile` aggregation + `CrossGamePattern` detection in `packages/heuristics/tests/test_account_profile.py`
- [ ] T064 [P] [US2] Write failing CLI integration test `apps/cli/tests/integration/test_audit_username.py` covering happy path, partial completion on Ctrl-C, and JSON shape per `contracts/cli-audit-username.md`

### Implementation for User Story 2

- [ ] T065 [US2] Implement `packages/analysis-core/src/analysis_core/ingest/chesscom_client.py` — `httpx` sync client, `User-Agent: cleanmatch/<version>`, 5 req/s polite limit, exponential backoff (turns T061-T062 green)
- [ ] T066 [US2] Implement `packages/heuristics/src/heuristics/scoring/account_profile.py` — per-game aggregation, weighted aggregate score, cross-game patterns (turns T063 green); depends on T056
- [ ] T067 [US2] Extend `packages/analysis-core/src/analysis_core/pipeline/run.py` with a `batch_run()` orchestrator that runs `audit-game` per fetched PGN with controlled `--max-concurrency`; signal handler captures Ctrl-C → `status=partial`
- [ ] T068 [US2] Implement `apps/cli/src/cleanmatch_cli/commands/audit_username.py` per `contracts/cli-audit-username.md` (turns T064 green); depends on T065-T067
- [ ] T069 [US2] Run the full US2 test suite and confirm coverage stays ≥85/80

**Checkpoint**: User Stories 1 AND 2 both work independently on canonical fixtures.

---

## Phase 5: User Story 3 — Timeline & move-level explainability (Priority: P3)

**Goal**: User opens a flagged run and inspects the timeline of plies plus per-move evidence.

**Independent Test**: For a known-suspect run produced by US1, `cleanmatch show <run-id>` prints a timeline distinguishing flagged from clean plies, and `cleanmatch show <run-id> --ply N` for any contributing ply shows top engine moves, complexity score, signal contributions, and a plain-language caption (FR-012; SC-003).

### Tests for User Story 3

- [ ] T070 [P] [US3] Write failing unit tests for the timeline renderer (one line per ply, classifications, flag markers) in `apps/cli/tests/unit/test_timeline_renderer.py`
- [ ] T071 [P] [US3] Write failing unit tests for the ply-detail renderer (top engine moves, eval delta, complexity, signal contributions, rationale) in `apps/cli/tests/unit/test_ply_renderer.py`
- [ ] T072 [P] [US3] Write failing CLI integration test `apps/cli/tests/integration/test_show.py` covering run-not-found (exit 1), batch-without-game-index (exit 1 with list), happy path human + JSON, and `--ply` focused mode per `contracts/cli-show.md`

### Implementation for User Story 3

- [ ] T073 [P] [US3] Implement `apps/cli/src/cleanmatch_cli/commands/show.py` orchestration: load run from disk, dispatch to timeline or ply renderer
- [ ] T074 [P] [US3] Implement timeline renderer in `apps/cli/src/cleanmatch_cli/output/timeline_renderer.py` (turns T070 green)
- [ ] T075 [P] [US3] Implement ply-detail renderer in `apps/cli/src/cleanmatch_cli/output/ply_renderer.py` (turns T071 green)
- [ ] T076 [US3] Wire renderers into `show` command; ensure SC-003 invariant (every flag cites ≥1 move, ≥1 signal, ≥1 principle) is enforced with a runtime check; depends on T073-T075 (turns T072 green)
- [ ] T077 [US3] Run the full US3 test suite

**Checkpoint**: User Stories 1, 2, 3 all work independently.

---

## Phase 6: User Story 4 — Auditable report bundle export (Priority: P4)

**Goal**: User exports a PDF + HTML + JSON + manifest bundle that reproduces deterministically.

**Independent Test**: `cleanmatch export <run-id> --out /tmp/case.zip` produces a zip containing the four files; running `export` twice yields byte-identical PDFs (same architecture) (SC-004; FR-014, FR-015, FR-017).

### Tests for User Story 4

- [ ] T078 [P] [US4] Write failing golden-file tests for the HTML render in `packages/report-engine/tests/test_render_html.py` (Jinja2 template against a pinned fixture run)
- [ ] T079 [P] [US4] Write failing golden-file tests for the JSON render in `packages/report-engine/tests/test_render_json.py`
- [ ] T080 [P] [US4] Write failing byte-stability test for the PDF render in `packages/report-engine/tests/test_byte_stability.py` (re-render → byte-identical bytes; same architecture)
- [ ] T081 [P] [US4] Write failing lexical-audit test in `packages/report-engine/tests/test_lexical_audit.py` that loads `tests/fixtures/forbidden-terms/{en,pt}.txt` and asserts every rendered artefact yields zero matches per category + match-mode (SC-008)
- [ ] T082 [P] [US4] Write failing CLI integration test `apps/cli/tests/integration/test_export.py` covering `--format bundle|pdf|html|json`, `--out` writable validation (exit 1 if not), and bundle structure per `contracts/cli-export.md`
- [ ] T083 [P] [US4] Write failing cross-architecture tolerance test `tests/e2e/test_cross_arch_tolerance.py` (skipped on single-arch CI; documents ±1 cp / ±0.001 score contract from FR-017)

### Implementation for User Story 4

- [ ] T084 [P] [US4] Implement Jinja2 templates under `packages/report-engine/src/report_engine/templates/` (`base.html`, `single_game.html`, `account_profile.html`, `manifest.html` partial)
- [ ] T085 [P] [US4] Implement `packages/report-engine/src/report_engine/render_html.py` (turns T078 green)
- [ ] T086 [P] [US4] Implement `packages/report-engine/src/report_engine/render_json.py` using Pydantic `model_dump_json` with sorted keys (turns T079 green)
- [ ] T087 [US4] Implement `packages/report-engine/src/report_engine/render_pdf.py` using WeasyPrint with a pinned `pydyf` version and deterministic metadata (no creation timestamp); depends on T084 (turns T080 green)
- [ ] T088 [P] [US4] Implement `packages/report-engine/src/report_engine/narrative.py` producing plain-language captions from `Narrative` / `FlaggedSegment` objects; per-language EN + PT (matches MVP language assumption)
- [ ] T089 [P] [US4] Implement matplotlib-SVG chart producers (timeline, complexity heatmap, eval graph) in `packages/report-engine/src/report_engine/charts.py` (seeded; byte-stable)
- [ ] T090 [US4] Implement bundling logic (`report.pdf` + `report.html` + `report.json` + `manifest.json` + `README.txt`) in `packages/report-engine/src/report_engine/bundle.py`; depends on T084-T089
- [ ] T091 [US4] Implement `apps/cli/src/cleanmatch_cli/commands/export.py` per `contracts/cli-export.md`; depends on T090 (turns T082 green)
- [ ] T092 [US4] Wire the lexical audit into `bundle.py` so an export with a forbidden-term match fails fast with `internal_error` exit 3 (turns T081 green at integration level)
- [ ] T093 [US4] Run the full US4 test suite

**Checkpoint**: All user stories independently functional. MVP is shippable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Performance budgets, packaging, observability, infra.

- [ ] T094 [P] Add performance benchmarks per constitution Principle IV in `packages/analysis-core/benchmarks/`: per-ply engine analysis ≤ 2.0 s @ depth 18 (`bench_engine_analysis.py`), 100-game chess.com ingest ≤ 5 s (`bench_chesscom_ingest.py`), 200-game RSS ≤ 1.5 GB (`bench_memory.py`)
- [ ] T095 [P] Add report-render benchmarks: ≤ 3 s p95 HTML and ≤ 8 s p95 PDF for a 50-game report in `packages/report-engine/benchmarks/bench_render.py`
- [ ] T096 [P] Wire benchmarks into CI as a separate job that runs on labelled PRs; regressions > 10% fail the job (per constitution Principle IV)
- [ ] T097 [P] Build `infra/docker/stockfish.Dockerfile` (pinned Stockfish 16.1 binary + SHA256 verification)
- [ ] T098 [P] Build `infra/docker/cleanmatch.Dockerfile` (multi-stage: uv build → slim runtime with Stockfish 16.1)
- [ ] T099 [P] Add `infra/compose/dev.yml` declaring Redis + Postgres services for future Phase 3 work (not required by MVP but reserved per plan)
- [ ] T100 [P] Add a `cleanmatch` console-script entry point in `apps/cli/pyproject.toml` so `pipx install` works end-to-end
- [ ] T101 [P] Documentation pass: ensure `specs/001-fairplay-analysis/quickstart.md` matches the actual install flow; add `docs/heuristics.md` summarising each signal module's owner, version, and changelog pointer (RNF-07)
- [ ] T102 [P] Add a PR template at `.github/pull_request_template.md` requiring (a) constitution principle check, (b) benchmark or budget-change note for changes under `packages/{analysis-core,heuristics,report-engine}`
- [ ] T103 Run the full test + benchmark suite, capture the coverage report, and update the README badge / quickstart with the actual reference numbers

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** — no dependencies; start immediately.
- **Phase 2 (Foundational)** — depends on Phase 1; BLOCKS all user stories.
- **Phase 3 (US1)** — depends on Phase 2 only. MVP target.
- **Phase 4 (US2)** — depends on Phase 2 + the score aggregator from US1 (T056).
- **Phase 5 (US3)** — depends on Phase 2 + the persisted run output from US1 (T057).
- **Phase 6 (US4)** — depends on Phase 2 + the `AuditRun` model and persisted artefacts from US1 (T013, T057).
- **Phase 7 (Polish)** — depends on the user stories that touch the surfaces being polished.

### User Story dependencies

- US1 has no dependency on other stories — pure MVP.
- US2 reuses the US1 per-game pipeline, but US2's *fetcher* and *aggregator* can be developed in parallel against `audit-game` as a stable contract.
- US3 reads runs persisted by US1; it does not modify pipeline code, so it can start in parallel with US2 work after US1 ships.
- US4 reads runs persisted by US1 + (optionally) US2; report-engine can be developed in parallel with US3 after US1 ships.

### Within each user story

- Tests MUST be written first and MUST fail before the corresponding implementation lands (constitution Principle II).
- Models before services; services before CLI wiring.
- Per-signal modules ([P]) are independent of each other but share the registry from T021.

### Parallel opportunities

- All Phase 1 `[P]` tasks run in parallel.
- All Phase 2 schema tasks (T009-T014) and all engine/manifest/cache tasks (T016, T017, T019) run in parallel; T018 depends on T017; T020 depends on T016-T019.
- Phase 3 unit-test files (T036-T044) are all `[P]` and run in parallel before any Phase 3 implementation begins.
- Phase 3 signal implementations T050-T055 are independent of each other.
- Phases 4, 5, 6 may proceed concurrently after Phase 3 ships (different developers / different files).

---

## Parallel Example: Phase 3 (US1) test bootstrap

```bash
# All red-first test files for US1 can be written in one parallel batch:
Task: "Write failing PGN loader tests in packages/analysis-core/tests/test_pgn_loader.py"        # T036
Task: "Write failing engine analysis tests in packages/analysis-core/tests/test_engine_analysis.py"  # T037
Task: "Write failing complexity tests in packages/heuristics/tests/test_complexity_analysis.py"  # T038
Task: "Write failing tactical-detection tests in packages/heuristics/tests/test_tactical_detection.py"  # T039
Task: "Write failing regime-shift tests in packages/heuristics/tests/test_regime_shift.py"       # T040
Task: "Write failing engine-correlation tests in packages/heuristics/tests/test_engine_correlation.py"  # T041
Task: "Write failing behavioral-patterns tests in packages/heuristics/tests/test_behavioral_patterns.py"  # T042
Task: "Write failing timing-analysis tests in packages/heuristics/tests/test_timing_analysis.py"  # T043
Task: "Write failing scoring tests in packages/heuristics/tests/test_scoring.py"                 # T044
Task: "Write failing CLI integration test in apps/cli/tests/integration/test_audit_game.py"      # T045
Task: "Write failing determinism integration test in apps/cli/tests/integration/test_determinism.py"  # T046
```

After all reds are green-checked-as-red, implementation tasks T047-T056 also run in parallel (different files).

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1: Setup.
2. Phase 2: Foundational (BLOCKS everything else).
3. Phase 3: User Story 1 — single-game audit.
4. **STOP and VALIDATE**: run the canonical fixtures end-to-end; confirm SC-001, SC-004, SC-007, SC-008 hold; benchmark Principle IV.
5. Ship if ready.

### Incremental delivery

1. Setup + Foundational + US1 → Ship MVP (probabilistic single-game audit).
2. Add US2 (batch by username) → ship updated CLI.
3. Add US3 (timeline + ply detail) → ship updated CLI.
4. Add US4 (export bundle) → ship the first "auditable report" release.

### Parallel team strategy

Once Phase 2 completes, three workstreams open in parallel:

- Workstream A (US1): pipeline + signals + scoring + `audit-game` CLI.
- Workstream B (US2 fetcher): chess.com client + backoff + filters; can develop against a fake pipeline until US1's contract stabilises.
- Workstream C (US4 report-engine): Jinja2 templates + render-PDF + lexical audit; can develop against a fake run on disk.

US3 typically follows US1 in the same workstream because it reads US1's persisted run output.

---

## Notes

- `[P]` tasks touch disjoint files.
- `[Story]` label maps each task to its user story for traceability.
- Tests MUST be written before their target implementation (constitution Principle II is NON-NEGOTIABLE).
- Coverage gate 85% line / 80% branch is enforced in CI on `packages/*/src/`.
- Performance budgets from constitution Principle IV are checked in Phase 7 and enforced thereafter via the `benchmarks/` CI job.
- Forbidden-terms list is the source of truth for SC-008 — adding a new term MUST come with a regression test ensuring no existing report or narrative breaks.
- Determinism contract (FR-017): bit-identical on same arch, ±1 cp / ±0.001 across arch.
- Commit after each task or logical group; never amend a commit that already passed CI.
- Stop at any checkpoint to validate user-story independence.
- Avoid: vague tasks, same-file conflicts inside a single phase, cross-story dependencies that break MVP independence.
