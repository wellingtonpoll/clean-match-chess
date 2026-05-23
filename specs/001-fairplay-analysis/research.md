# Phase 0 Research — Probabilistic Fair Play Analysis Platform

**Feature**: `001-fairplay-analysis` · **Date**: 2026-05-23

This document records the stack and design decisions taken before Phase 1
contract work. Each decision lists what was chosen, why, and the alternatives
that were considered and rejected. No `NEEDS CLARIFICATION` markers remain.

---

## 1. Monorepo tooling — Python workspace

- **Decision**: `uv` workspaces (PEP 621 + `uv.lock` at repo root, per-package
  `pyproject.toml`). One Python version pinned to 3.11 across all packages.
- **Rationale**: `uv` is fast, deterministic, and supports workspace
  resolution without inventing a custom multi-repo glue layer. Single lockfile
  makes the reproducibility manifest trivial.
- **Alternatives considered**:
  - Poetry workspaces — slower resolver, weaker workspace semantics.
  - PDM — viable, but `uv` has better CI ergonomics and is already trending
    inside the broader Python data-science / engines ecosystem.
  - Plain `pip-tools` per package — too much hand-coordination for shared
    locks.

## 2. CLI framework

- **Decision**: `typer` for the `apps/cli` entry point.
- **Rationale**: Type-hint-driven, matches `mypy --strict` discipline,
  generates `--help` that already includes flag types and defaults. Clean
  mapping from constitution Principle III (exit codes, structured JSON
  output, kebab-case subcommands).
- **Alternatives considered**:
  - `argparse` — verbose, no type inference, manual help wiring.
  - `click` — fine, but `typer` is a thin wrapper that produces less
    boilerplate while still building on `click` under the hood.

## 3. Chess engine integration

- **Decision**: `python-chess` for PGN/UCI/board manipulation;
  `stockfish` binary 16 invoked via the `python-chess` `engine.SimpleEngine`
  UCI interface inside our own pool (`packages/analysis-core/engine/`).
- **Rationale**: `python-chess` is the de facto standard library for chess
  parsing in Python; pairing it with a directly-controlled Stockfish binary
  gives us precise control over depth, threads, hash, and MultiPV — all of
  which are required by FR-004 and constitution Principle IV.
- **Engine settings pinned in MVP**:
  - Depth: 18.
  - Threads: 1 per worker (parallelism comes from running multiple workers,
    not multithreading a single search — avoids non-determinism Stockfish
    introduces with `Threads > 1`).
  - Hash: 256 MB per worker.
  - MultiPV: 5.
  - `Use NNUE`: true (Stockfish 16 default).
- **Alternatives considered**:
  - `python-stockfish` wrapper package — convenient but hides UCI options
    that we need to pin. Rejected.
  - Lc0 only — produces different signals, attractive for hybrid analysis,
    but adds GPU/CPU complexity in MVP. Deferred to a follow-up feature.

## 4. Determinism guarantee

- **Decision**: Each `AuditRun` records an explicit manifest containing
  engine binary SHA256, engine UCI options, heuristic package versions
  (semver) and their git SHAs, input PGN SHA256, and library versions of
  `python-chess` + `analysis-core`. The pipeline refuses to mix runs across
  manifest values when reading from the cache.
- **Rationale**: FR-017 (bit-identical re-runs) is the central forensic
  guarantee. The manifest is the audit primitive that makes reproducibility
  measurable rather than aspirational.
- **Threats**:
  - Stockfish + `Threads > 1` introduces search non-determinism →
    constrained to `Threads = 1` (above).
  - Floating point in heuristics: decisions either use `Decimal` for the
    aggregator or operate purely on integer cp evaluations → enforce via
    lint rule (`ruff` custom check or `mypy` plugin to be evaluated).

## 5. chess.com ingestion

- **Decision**: `httpx` (sync client in MVP) against the public endpoints
  `https://api.chess.com/pub/player/{username}/games/{YYYY}/{MM}` plus the
  monthly archive index. Polite defaults: `User-Agent: cleanmatch/<version>
  (contact: <project-url>)`, exponential backoff on 429/5xx, max 3 retries,
  request budget 5 req/s.
- **Rationale**: Public API is documented, requires no auth, and returns PGNs
  directly. Sync client is enough for MVP volumes; we can upgrade to async
  inside the Phase 3 worker without changing the contract.
- **Alternatives considered**:
  - Scraping chess.com HTML — fragile, may violate ToS.
  - Lichess only — Lichess API is also free and arguably cleaner, but the
    spec assumption locks MVP to chess.com (primary audience).
  - Async client (`httpx.AsyncClient` + `anyio`) — useful in workers but
    overkill for a single-user CLI; keep simple.

## 6. Signal package versioning

- **Decision**: Each subpackage of `packages/heuristics/src/heuristics/*`
  declares a `__signal_version__` semver string and an entry in
  `registry.py`. The registry's `signals_for(game)` returns a frozen tuple
  of `(name, version, callable)` tuples. Manifests record exact versions
  contributing to an `AuditRun`.
- **Rationale**: Satisfies RNF-07 and constitution Principle II's audit
  requirement. Lets us evolve heuristics (e.g., from v0.2 to v0.3) without
  invalidating older reports' interpretation.
- **Alternatives considered**:
  - Single monolithic heuristic module — easier short-term, but defeats
    DRS §10 modularity and makes per-signal versioning impossible.

## 7. Aggregation & risk classification

- **Decision**: Score is a weighted sum of per-segment signal contributions,
  normalised to `[0, 1]`. Risk levels mapped to fixed thresholds:
  `low < 0.35`, `0.35 ≤ medium < 0.70`, `high ≥ 0.70`. Confidence interval
  produced by bootstrap resampling of per-move contributions (N=1000).
  Thresholds are stored in `packages/heuristics/src/heuristics/scoring/
  thresholds.py` and are themselves versioned.
- **Rationale**: Conservative aggregation aligned with Principle 3 (false
  positives are critical failures). Bootstrap CI gives a defensible
  uncertainty number without requiring a labelled training corpus we
  don't yet have.
- **Alternatives considered**:
  - Logistic regression / GBDT on hand-labelled data — needs a labelled
    corpus the project has not yet curated; deferred until Phase 4
    longitudinal data exists.
  - Bayesian posterior with informative priors — promising but premature.

## 8. Opening-book discount (Principle 6)

- **Decision**: Use an embedded Polyglot opening book (`book.bin`)
  derived from a public corpus of master games. A ply is considered "book"
  if (a) the position's hash exists in the book and (b) the move played
  appears as a book move with non-trivial weight. Book plies are excluded
  from scoring but reported as `book_plies` in the manifest.
- **Rationale**: Cheap and deterministic; Polyglot books are stable,
  redistributable, and pin to a SHA in the manifest. Satisfies
  Principle 6 + spec FR & SC-007.
- **Alternatives considered**:
  - ECO-code-only heuristic — too coarse, mislabels novel transpositions.
  - Querying chess.com / Lichess opening explorer — adds network dep and
    is non-deterministic.

## 9. Report rendering

- **Decision**: HTML rendering via `Jinja2`; PDF via `WeasyPrint` from the
  same HTML template. JSON rendering via Pydantic's `model_dump_json`.
  Charts (timeline, complexity heatmap, eval graph) generated server-side
  as SVG using `matplotlib` with a non-interactive backend, embedded
  directly into the HTML/PDF — no JS dependency at MVP.
- **Rationale**: `WeasyPrint` reuses the HTML layout, so we maintain one
  template instead of two; this aligns with constitution Principle I
  (single source of truth). `matplotlib` SVGs are byte-stable when seeded
  → fits determinism.
- **Alternatives considered**:
  - Playwright PDF — heavyweight (requires headless Chromium); deferred
    to Phase 3 where it can be reused for screenshot regression tests.
  - ECharts SSR — beautiful but adds Node toolchain to MVP; defer until
    `apps/frontend` exists.

## 10. Observability (MVP scope)

- **Decision**: `structlog` for structured logging in the CLI with two
  formatters — pretty (default, to stderr) and JSON (when
  `--log-format=json` or `CLEANMATCH_LOG_FORMAT=json`). No Loki /
  Prometheus / Grafana in MVP; instrument once `apps/api` exists.
- **Rationale**: Matches constitution Principle III and avoids dragging
  in infrastructure that is irrelevant to a single-machine CLI.

## 11. Testing strategy

- **Decision**:
  - Per-package `tests/` with `pytest` and `pytest-cov`.
  - Pinned PGN fixtures under `tests/fixtures/pgn/known-clean/` and
    `tests/fixtures/pgn/known-suspect/`.
  - Pinned Stockfish output snapshots stored as JSON in
    `tests/fixtures/stockfish/<engine-sha>/<pgn-sha>/<ply>.json`. The
    engine pool reads from these snapshots in unit-test mode so the test
    suite does not require Stockfish to be installed.
  - End-to-end CLI tests under `apps/cli/tests/integration/` exercising the
    real Stockfish binary on a small (10-game) reference set, marked
    `@pytest.mark.slow` and gated by `CLEANMATCH_E2E=1` in CI.
  - Coverage gate **85% line / 80% branch** on `packages/*/src/` per
    constitution Principle II.
  - Benchmarks under each package's `benchmarks/` directory, run via
    `pytest-benchmark`; thresholds enforced in CI.

## 12. Concurrency model in MVP

- **Decision**: Single OS process orchestrates a pool of
  `multiprocessing.Process` workers, one Stockfish binary per worker. Game
  ingestion is sync (`httpx`); engine analysis is the only thing
  parallelised; report generation is sync.
- **Rationale**: Stockfish dominates CPU. Multiprocessing avoids the GIL
  cleanly, gives one engine per core, and matches the deterministic
  `Threads=1` setting. AsyncIO is reserved for the Phase 3 web/worker
  rewrite.

## 13. Storage layout (MVP)

- **Decision**: All durable artefacts go under
  `${CLEANMATCH_HOME:-~/.cleanmatch}/`:
  - `pgn-cache/<source>/<sha>.pgn` — raw PGN cache.
  - `runs/<run-id>/manifest.json` — reproducibility manifest.
  - `runs/<run-id>/positions.json` — per-position analysis records.
  - `runs/<run-id>/score.json` — aggregated score + per-segment + CI.
  - `runs/<run-id>/report.{html,pdf,json}` — rendered reports.
  - `runs/<run-id>/audit.log` — per-run structured log.
- **Rationale**: Filesystem-only storage keeps determinism trivial, avoids
  Postgres dependency in MVP, and lets users zip a directory and share.
  Layout mirrors a future Postgres schema cleanly (`runs` table).

## 14. Cross-cutting decisions deferred to later phases

- **Auth / Auth.js**: irrelevant in MVP CLI (single local user).
- **Redis / Dramatiq / Celery**: not needed until `apps/api` ships in
  Phase 3.
- **PostgreSQL / TimescaleDB / pgvector**: not needed until Phase 3;
  filesystem layout above is the migration source.
- **MinIO**: same — not needed until artefacts are served over HTTP.
- **Kubernetes**: explicitly out of scope (project memory + user input).

---

**Outcome**: All Technical Context items are resolved. Phase 1 can proceed.
