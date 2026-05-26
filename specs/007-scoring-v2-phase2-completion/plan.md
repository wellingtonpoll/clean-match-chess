# Implementation Plan: Scoring v2 Phase 2 Completion

**Branch**: `007-scoring-v2-phase2-completion` | **Date**: 2026-05-25 (rev 2026-05-26 T007 v2) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-scoring-v2-phase2-completion/spec.md`

## Summary

Close all four deferrals from Feature 005 (CHANGELOG.md:139-153 `Pending (Feature 005)`): real measured rating baselines (replaces literature stub), ≥20 engine-assisted PGN fixtures, full FPR-gate validation run, and measured-metric documentation in CHANGELOG. Unblocks `[2.1.0]` release. Technical approach: implement the currently-unimplemented `build_buckets_real()` in `packages/heuristics/scripts/build_baselines.py` (streams the Lichess 2026-04 archive via `zstdcat`, reservoir-samples 5000 games per bucket with seed=0 deterministic RNG, runs SF16 depth 10 over the 30 000 sampled games, writes schema-valid JSON), then runs the full FPR-gate against real baselines + real engine-assisted corpus.

**T007 v2 (2026-05-26)** — after the v1 build lost 30k in-RAM analyses to a `ProcessPoolExecutor` shutdown hang (podman engine handles never released), the build pipeline was redesigned around Postgres persistence (feature 008 DB infra). Every Stockfish analysis lands in `baseline_analyses` the moment it completes; Phase-1 reservoir state flushes every 100k games scanned. A crash anywhere loses at most ~one in-flight analysis or one flush window. Restart via `--run-id <uuid>` re-claims pending samples. Production rollout via `pg_dump --table=baseline_* --table=pgn_corpus`. Detailed plan in `/home/mestre/.claude/plans/smooth-jumping-lightning.md`.

## Technical Context

**Language/Version**: Python 3.12 (uv-managed workspace)

**Primary Dependencies**: `python-chess` (PGN parsing, streaming via `chess.pgn.read_game`), Stockfish 16 (depth-12 analysis), `zstandard >= 0.22, < 1.0` (new — for `zstdcat` subprocess wrapper)

**Storage**: JSON artefact at `packages/heuristics/data/rating_baselines.json` (~6.5 KB); intermediate Phase-1 sampling checkpoints at `/tmp/baselines-007/*.sample.pgn` (gitignored, ~30 MB total)

**Testing**: pytest with `StaticAnalyzer` dependency-injection for `build_baselines.py` unit tests (no real Stockfish in CI). Full FPR-gate run for end-to-end validation. `pytest --cov --cov-fail-under=85` (Principle II).

**Target Platform**: Linux maintainer machine (build script); CI on `ubuntu-latest` for unit tests + FPR-gate cold-cache run

**Project Type**: Python monorepo with `packages/{heuristics,analysis-core,shared-types}/`; one-shot maintainer script in `packages/heuristics/scripts/`

**Performance Goals**: Build pass ≤ 8 h wall-clock; FPR-gate warm budget ≤ 5 min, cold ≤ 30 min (per Feature 005 R5)

**Constraints**:
- Determinism (`random.Random(seed)` only — no module-level `random`)
- Cannot relax `fpr ≤ 0.02` / `tpr ≥ 0.80` per FR-010
- Cannot modify schemas (locked by 004 / 005 contracts)
- Cannot commit source archive (28 GB, `.gitignore`'d)

**Scale/Scope**:
- Input: ~80M games in the Lichess 2026-04 archive (~170 GB decompressed PGN stream)
- Filtered + sampled: 30 000 games (5000 × 6 buckets)
- Analyzed: 30 000 games × ~80 plies × Stockfish depth 12 ≈ 45 CPU-hours

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I — Code Quality**: PASS. New `build_buckets_real()` will ship with type hints + docstrings; `uv run ruff check . && uv run ruff format --check .` and `uv run mypy --strict` are gates in Phase 6 (T021 / T022).
- **Principle II — Testing NON-NEGOTIABLE**: PASS. Unit tests with `StaticAnalyzer` injection cover filter logic, reservoir determinism, bucketing edges, schema validation, and the `rating-unknown` median path — no real Stockfish needed in CI. `pytest --cov --cov-fail-under=85` enforced (T023).
- **Principle III — UX Consistency**: PASS. `build_baselines.py` is a CLI maintainer script; exit codes (0 success, 1 user error, 2 upstream fail) follow constitution; `--output json` already a default; errors name the deficient bucket per FR-001 acceptance.
- **Principle IV — Performance Requirements**: PASS. No change to per-ply engine-analysis budget (≤ 2 s/ply at depth 18). FPR-gate cold-cache budget already in 005 R5 (≤ 30 min); warm ≤ 5 min preserved by reusing the existing `tests/fixtures/corpora/.cache/` keyed on `engine_binary_sha256` + `opening_book_sha256`.

**No violations. No complexity-tracking entries needed.**

## Project Structure

### Documentation (this feature)

```text
specs/007-scoring-v2-phase2-completion/
├── plan.md              # This file
├── spec.md              # Feature specification (already written)
├── research.md          # Phase 0 — decisions D1–D8
├── tasks.md             # Phase 2 — T001–T025
├── quickstart.md        # Phase 1 — one-command recipes per phase
├── HANDOFF.md           # Maintainer 6-hr build checklist
├── contracts/           # (no new contracts; reuses 004 + 005 schemas)
└── checklists/
    └── requirements.md  # Spec quality gate
```

### Source Code (repository root)

```text
packages/heuristics/
├── pyproject.toml                       # +zstandard dep (T002)
├── scripts/
│   └── build_baselines.py               # rewrite build_buckets_real() (T004)
├── tests/
│   └── test_build_baselines.py          # new unit tests (T005)
└── data/
    ├── rating_baselines.json            # regenerated by T007 (real data)
    └── README.md                        # new — provenance record (T018)

tests/fixtures/corpora/
├── engine_assisted/                     # populated by T010 (≥20 PGNs + provenance)
└── .cache/                              # FPR-gate engine-analysis cache (gitignored)

tests/fpr_gate/                          # existing harness — reused unchanged

infra/docker/
└── stockfish.Dockerfile                 # existing — used by T003 for SF16 image
```

**Structure Decision**: Maintainer-script + data-artefact pattern. No new packages, no new modules. The only Python source change is rewriting one function (`build_buckets_real`) and adding one test module. Everything else is data updates + documentation.

## Complexity Tracking

*No violations. Section intentionally empty.*
