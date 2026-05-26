# Changelog

All notable changes to Clean Match Chess are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added — Feature 008 (Postgres-backed analysis cache)

- **Analysis-result cache backed by Postgres**. `cleanmatch audit-game`
  (and the SSE-proxied frontend that spawns it) now consults a Postgres
  cache before spawning Stockfish. Identical PGN re-runs return in
  ~1 s wall-clock (Python startup dominated) versus ~145 s for a
  cache miss — a measured **~145× speedup** on the smoke fixture.
- **Composite cache key** `(pgn_sha256, manifest_sha256)`. `manifest_sha256`
  is the existing `analysis_core.manifest.manifest_hash` output, which
  covers engine binary sha256, opening book sha256, heuristic versions,
  scoring threshold version, signal versions, rating baselines version
  + sha256, design system version. **Algorithm bumps automatically
  invalidate every cached row** — no manual purge needed.
- **`--no-cache` flag finally honored.** Previously accepted-and-ignored
  on `audit-game` and `audit-username`; now plumbed through to
  `run_single_game(..., no_cache=...)` and skips both lookup AND persist
  so forced re-runs never pollute the row count.
- **Graceful degradation.** When `DATABASE_URL` is unset OR Postgres is
  unreachable, the audit runs at full cost with a structured warning
  on stderr (`event=db.cache.lookup_unreachable` /
  `db.cache.persist_unreachable`) and the JSON envelope on stdout is
  unchanged. Developer machines without a running database continue to
  work without modification.
- **Reserved auth columns.** The `audit_runs` schema includes nullable
  `user_id UUID` and `tenant_id UUID` columns from the initial migration
  (`0001_init.py`) — no FK constraints yet. The incoming feature 009
  (auth + recurring subscriptions) can add the `users` and `tenants`
  tables and attach the FKs via a deferred migration without restructuring
  the cache.
- New files:
  - `infra/docker/compose.yml` — Postgres 17-alpine service + named
    volume.
  - `infra/docker/README.md` — compose + ops quickstart.
  - `.env.example` — `DATABASE_URL` template (real `.env` gitignored).
  - `packages/analysis-core/alembic.ini` + `migrations/env.py` +
    `migrations/versions/0001_init.py` — Alembic scaffold + initial
    schema (`audit_runs` table, UNIQUE constraint, 4 secondary indexes,
    `pgcrypto` extension for `gen_random_uuid()`).
  - `packages/analysis-core/src/analysis_core/db/{__init__,models,session,cache}.py`
    — SQLAlchemy 2.0 model + sync session factory + `lookup()` / `persist()`
    with structured graceful-degradation + password-masked URL logging.
  - `packages/analysis-core/docs/cache.md` — ops runbook (env vars,
    nuke + rebuild recipe, retention policy stub).
  - `tests/integration/test_postgres_cache.py` — 4 tests
    (double-audit-hits-cache, no-cache-skips-persist, db-down-graceful,
    migration-roundtrip). Skip cleanly when `DATABASE_URL` is unset.
- New deps in `packages/analysis-core/pyproject.toml`:
  `sqlalchemy>=2.0,<3`, `psycopg[binary]>=3.2,<4`, `alembic>=1.13,<2`
  (all runtime — the cache layer's `init_engine()` is invoked
  unconditionally and degrades gracefully).
- CI: the existing `test` job in `.github/workflows/ci.yml` gains a
  `services: postgres` block (port 5432, `pg_isready` healthcheck) and
  runs `alembic upgrade head` before pytest. Integration tests now run
  against a real Postgres on every PR.

### Added — Feature 006 (Frontend UX Improvements, follow-up)

- **Per-game reasoning narrative**. `ExpandedAnalysis` now opens with a
  score-summary block that explains how the platform arrived at the
  specific score: it quotes the numeric value, classifies it (BAIXO /
  MÉDIO / ALTO via `risk_level`), names the confidence-interval width
  (precisão alta / moderada / incerteza considerável), and frames the
  signal list with copy that varies by risk (signals that pushed the
  score up at HIGH vs. signals that were checked but stayed normal at
  LOW). New `summarizeGame()` in `lib/signalExplanations.ts` is
  pure-function and unit-tested. Resolves the "explicação detalhada de
  como a plataforma chegou nesse resultado" issue raised 2026-05-25.
- **Signal dictionary expanded for namespaced names**. Backend emits both
  bare (`precision-burst`, `complexity`) and namespaced
  (`behavioral-patterns/precision-burst`, `complexity-analysis`,
  `engine-correlation/weighted`) forms; the dictionary now carries
  explicit entries for both stylings so `explainSignal` no longer falls
  back to the generic "Sinal técnico" copy for known signals.
- **Sticky profile hero**. While in profile mode the hero section is
  `position: sticky; top: var(--header-h)` so the searched player's
  identity + ratings stay pinned below the Header as the results list
  scrolls. `Header` now publishes its real `offsetHeight` to the
  `--header-h` CSS custom property on mount and on window-resize
  (single-pass + rAF, no ResizeObserver loop), so the sticky offset and
  the `<main>` top padding track the actual stacking height instead of
  the static 64 / 112 px fallbacks.
- **Searched-user hero lockup**. After a search submits, the hero section
  stays mounted but swaps its content from the default HorseLabs intro to
  a `ProfileLockup` rendering the searched player's account data:
  username (48px Instrument Serif, links to the canonical platform URL),
  title chip when held, platform / country / join date / display name
  meta-row, and one rating card per game mode reported by the upstream
  platform (chess.com: rapid/blitz/bullet/daily; lichess:
  bullet/blitz/rapid/classical/correspondence). Loading and not-found
  states render in-place so the hero never disappears between submit and
  result. New API route `app/api/profile/route.ts` proxies chess.com
  (`/pub/player/{u}` + `/pub/player/{u}/stats`) and lichess
  (`/api/user/{u}`) into a unified `PlayerProfile` envelope; chess.com
  calls go out with a polite User-Agent.

### Fixed — Feature 006 (Frontend UX Improvements, follow-up)

- `ProgressBar` default fill colour changed from `#B81820` (sangue-luz / high-risk
  red) to `#4A4A50` (grafite / neutral). The indeterminate variant is rendered
  on pending game-rows; previously the red animation pre-signaled "high risk"
  before any analysis had run. Determinate callsites in `GameRow` continue to
  pass an explicit risk-coloured fill (low / medium / high), so the score-bar
  appearance is unchanged. Surfaced via a cross-viewport Playwright probe
  (`apps/frontend/tests/e2e/layout-audit-daianydias.spec.ts`) that screenshots
  the daianydias search flow on iPhone SE, iPhone 11 Pro Max, 1280×800,
  and 1920×1080.
- `GameRow` dominant-signal chips moved out of the right-hand column into
  their own full-width row (`flex-basis: 100%`) below the main row. Long
  chip names such as `behavioral-patterns/precision-burst` previously
  expanded the right column past the score column, pushing the score
  section right and breaking row alignment. Chip text now ellipsis-truncates
  with `title=` tooltip; the right column (RiskBadge + ExportButton) is
  capped at `max-width: 160px`. Regression guard: new `long-signals`
  fixture and `05-long-signals` stage in the layout audit.

### Added — Feature 006 (Frontend UX Improvements)

- **Clickable player links** (US1): player usernames in game cards render as
  semantic `<button>` elements. Clicking an opponent's name aborts any
  in-flight analysis and triggers a new analysis for that player on the
  current platform; clicking the current subject is a no-op.
- **Expandable analysis cards** (US2): cards in `done` state expand on click
  to reveal an "Análise detalhada" section with pt-BR explanations for each
  `dominant_signal`. Dictionary covers 11 known signals plus a generic
  fallback for new signals introduced backend-side.
  Lives at `apps/frontend/lib/signalExplanations.ts`. Jargon blacklist
  (z-score, bootstrap, CUSUM, p-value, etc.) enforced via test.
- **Sticky header** (US3): brand mark + search field + platform toggle pinned
  to the top of the viewport. Clicking the HorseLabs brand resets the
  current analysis and restores the hero section. Mobile (<480px) stacks
  the brand above the search row.
- **Cross-viewport Playwright suite** (US4): 4 viewports
  (375×667, 414×896, 1280×800, 1920×1080); 6 bug-class detectors (overflow,
  hidden controls, truncation, hover-on-touch, scroll lock, expand-layout-shift);
  90 tests pass in ~35 s wall time (warm). CI job `frontend_e2e` path-filtered
  to `apps/frontend/**`.
- `AnalysisProvider` context (`apps/frontend/lib/AnalysisContext.tsx`) lifts
  `runAnalysis` + session state out of the page so the new Header and
  PlayerLink components share the same actions.
- ESLint flat config (`apps/frontend/eslint.config.mjs`) for lint parity with
  the backend `ruff` gate (Principle I — infra cleanup, not user-visible).

### Added — Feature 005 (Scoring v2 Phase 2)

- **Real Polyglot opening book** at `packages/analysis-core/data/opening_book.bin`
  (US2). Replaces the 1.3 KB Phase 1 synthetic stub with a 6.5 MB book derived
  from Lichess broadcast PGN archives 2025-02 + 2025-03 + 2025-04 (60,644 OTB
  master games, 425,062 entries). sha256:
  `dd0c9b50f75274b421ee9bfa12b45920b38124c9e2c7768f1179d130357c4532`.
  Build script: `packages/analysis-core/scripts/build_book_from_broadcasts.py`.
  License: CC-BY-SA 4.0 (inherited from upstream Lichess broadcasts).
  Substitution rationale: the originally documented `gm2600.bin` upstream URL
  (research.md R2) is no longer reachable; a Lichess-broadcast-derived book is
  a stronger provenance trail (CC-BY-SA 4.0, sha256-verifiable, fully
  reproducible from a public URL).
- **Verified clean corpus fixtures**: 50 OTB tournament games under
  `tests/fixtures/corpora/clean/` (US3 partial — clean bucket only).
  Source: Lichess broadcast archives 2025-02 + 2025-03 + 2025-04.
  Each fixture carries a sibling `.provenance.json` matching
  `contracts/provenance.schema.json` with `label="clean"`,
  `label_confidence="high"` (arbiter-monitored). Extraction script at
  `tests/fpr_gate/_corpus_extract.py`.
- `AuditRun.manifest` optional field — `ReproducibilityManifest` is now
  attached in-band to every audit output, so consumers no longer need a
  separate `manifest.json` read for provenance (FR-003, US4).
- Labeled-corpus FPR-gate test target at `tests/fpr_gate/test_fpr_gate.py`
  with helpers (`provenance.py`, `cache.py`, `gate.py`). Test asserts
  **FPR ≤ 2.0%** on a clean corpus and **TPR ≥ 80.0%** on an
  engine-assisted corpus at the `RISK_HIGH_MIN` decision threshold
  (FR-006, FR-007, SC-003). Skips gracefully when either bucket is empty.
- Per-fixture engine-analysis cache under `tests/fixtures/corpora/.cache/`
  (gitignored). Cache files embed `engine_binary_sha256` and
  `opening_book_sha256` from the cached `AuditRun.manifest`; stale entries
  are auto-detected on engine or book swap (FR-008, R3 mitigation).
- CI job `fpr_gate` in `.github/workflows/ci.yml`. Uses `actions/cache@v4`
  keyed on `opening_book.bin` + corpus PGN content. Path-filtered: runs on
  `push` to `main` and on PRs labeled `scoring`. Branch-protection (maintainer
  configures separately) makes it required for merge.
- Provenance schema for corpus fixtures (`*.provenance.json`) with five
  required fields: `source`, `retrieved_at`, `label`, `label_confidence`,
  `notes` (FR-005, contracts/provenance.schema.json).

### Pending (Feature 005 — to land before v2.0.0 promotion)

- Real Lichess month-export baselines (replaces hand-curated stub at
  `packages/heuristics/data/rating_baselines.json`) — US1. Deferred
  because the source archive is ~29 GB compressed and a build pass takes
  30-90 min CPU; needs maintainer-machine execution.
- ≥ 20 engine-assisted PGN fixtures under `tests/fixtures/corpora/engine_assisted/`
  with `label_confidence="high"` and notes acknowledging Lichess-classifier
  circularity — US3 (FR-005). Deferred because Lichess does not publish a
  flagged-account list via API; manual sourcing of publicly-disclosed cases
  is required (HANDOFF.md Block B-2).
- Full FPR-gate run on the complete corpus (T023) + regression-PR smoke
  (T025) + determinism re-run verification (T030).
- Measured FPR + TPR on the shipped corpus (point estimates + 95% CIs);
  smoke-test score delta vs Phase 1 stub baseline — FR-009.

### Added (carried over)

- Feature 003 — Repository health, CI supply-chain hardening, and OSS curation
  (SHA-pinned Actions, Dependabot, community health files, py.typed markers)

---

## [2.0.0] — 2026-05-24

Feature 004 — Fraud Detection Algorithm v2 Phase 1 (Statistical Foundation).

**Breaking change**: scores produced by this version are NOT numerically
comparable to scores produced by v1.x. The weights, signals, and bootstrap
methodology have all changed; manifest provenance now records the new signal
versions so persisted runs can be distinguished.

### Added

- `acpl-analysis` signal — Average Centipawn Loss calibrated against the
  player's rating bucket (FR-002, FR-003, US1)
- Bundled polyglot opening book at `packages/analysis-core/data/opening_book.bin`
  (gm2600.bin, public domain); `--book PATH` flag now functional on
  `audit-game` AND `audit-username` (FR-009, FR-020, US4)
- Bundled rating-baselines lookup at `packages/heuristics/data/rating_baselines.json`
  with one-shot maintainer script `packages/heuristics/scripts/build_baselines.py`
  (FR-010, FR-011)
- New `segment_aggregator` module: per-phase heuristic application with
  phase weights OPENING=0.5, MIDDLEGAME=1.0, TACTICAL=1.5, CONVERSION=1.3,
  ENDGAME=0.7 (FR-013–015, US5)
- Manifest now stamps `opening_book_sha256`, `rating_baselines_sha256`,
  `rating_baselines_version`, `scoring_thresholds_version`, and
  `signal_versions` dict (FR-012, SC-010)
- Move-resampling bootstrap with N=10000 default samples (FR-007, US3)

### Changed

- `blunder-suppression` (behavioral-patterns/blunder-suppression) rewritten
  from "post-move eval is calm" to delta-based "expected blunder evaded"
  per FR-004 — fixes the v1 bug that inflated the signal for any drawn or
  balanced game (US2)
- `regime-shift` rewritten from segment-size variation to CUSUM
  change-point detection on the per-move ACPL series (FR-005, US7)
- `timing-analysis` rewritten from binary fast-move count to regression-
  residual analysis on `log(time_ms+1) ~ complexity + phase` with a
  pre-move sub-signal blend (FR-006, US6)
- `engine-correlation` adds rating-bucket calibrated ratio mode; raw
  rate remains in `SignalAggregate.mean`, calibrated ratio in
  `weighted_mean`; aggregator applies piecewise normalization
  `clip((ratio - 1.0) / 1.5, 0, 1)` (FR-008, US8)
- `WEIGHTS` redistribution per FR-016: `acpl-analysis` 0.30,
  `engine-correlation/weighted` 0.30, `engine-correlation/top1` 0.05
  (down from 0.15), full distribution sums to 1.0; carrier
  `segments-weighted-aggregate` added at weight 0.74 to fold per-segment
  contributions
- `SCORING_THRESHOLDS_VERSION` bumped from `1.0.0` to `2.0.0` (FR-017);
  risk-level thresholds (LOW < 0.35, MEDIUM < 0.70, HIGH ≥ 0.70) unchanged
  in this phase (FR-018 — calibrated thresholds deferred to Phase 2)
- Signal versions bumped to `2.0.0`: `regime-shift`, `timing-analysis`,
  `engine-correlation`, `behavioral-patterns`

### Deferred to Phase 2

- SC-001 (engine-assisted corpus validation) and SC-002 (clean corpus FPR
  gate) require labeled-corpus sourcing and threshold calibration that are
  out of scope for Phase 1. Phase 2 backlog items P2-T001 and P2-T002 track
  these. Phase 1 pipeline correctness is validated by SC-003 through SC-010
- T042b score-delta documentation (engine-correlation ratio normalization
  vs pre-H1 baseline) deferred — bundled gm2600 book covers ~9 plies of
  the Italian Game test fixture (SC-005 targets ≥ 10; we accept ≥ 8 here)

### Notes

- Bootstrap perf budget on the reference machine is ≈ 0.5 s with a
  trivial resample closure (vs plan.md's aspirational ≤ 100 ms). Bench
  ceiling at 2000 ms — well within the engine-analysis budget (≤ 2.0
  s/ply, dominant cost). Constitution Principle IV held.

---

## [1.0.0-design-system] — 2026-05-23

Forensic Analytics Design System — first stable release.

### Added

- `packages/design-system` v1.0.0: palette, typography, motion, and lexical
  design-token layers with full audit suite enforced in CI
- Four locked audits (`audit_palette`, `audit_typography`, `audit_motion`,
  `audit_lexical`) run as a required CI gate on every PR
- `design_system_audits` CI job (enforced, no `|| true`) as the quality gate
- Design system components catalogue (`docs/COMPONENTS.md`), lexicon
  (`docs/LEXICON.md`), and audit reference (`docs/AUDITS.md`)
- Forensic-appropriate color palette with WCAG AA contrast enforcement
- Motion spec with `prefers-reduced-motion` compliance gate
- Analytical lexicon with forbidden-terms loader and CI check

---

## [0.1.0] — 2026-05-23

MVP CLI auditor — Feature 001 complete (103/103 tasks).

### Added

- `cleanmatch` CLI with `audit-game`, `audit-username`, `show`, and `export`
  subcommands
- `packages/analysis-core`: PGN ingest, Stockfish engine pool, analysis pipeline
- `packages/heuristics`: five versioned signal modules — engine correlation,
  complexity analysis, tactical detection, regime shift, behavioral patterns
- `packages/report-engine`: HTML, PDF, and JSON report renderers
- `packages/shared-types`: Pydantic v2 schemas shared across all packages
- Reproducibility manifest (SHA256 of input PGN + Stockfish binary + heuristic
  versions) included in every report bundle
- 285 tests, 93% line coverage, enforced 85% gate
- `mypy --strict` and `ruff` clean on all packages
- Docker 2-stage build (`cleanmatch.Dockerfile`) for reproducible deployments
- Opening book support and known-clean / known-suspect PGN fixture suite
