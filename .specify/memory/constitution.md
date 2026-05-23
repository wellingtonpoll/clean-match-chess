<!--
Sync Impact Report
==================
Version change: 0.0.0 (template placeholders) → 1.0.0
Rationale: Initial ratification of the project constitution. MAJOR bump from the
template's unfilled state to a fully defined v1 governance baseline.

Modified principles:
  - [PRINCIPLE_1_NAME] → I. Code Quality
  - [PRINCIPLE_2_NAME] → II. Testing Standards (NON-NEGOTIABLE)
  - [PRINCIPLE_3_NAME] → III. User Experience Consistency
  - [PRINCIPLE_4_NAME] → IV. Performance Requirements
  - [PRINCIPLE_5_NAME] removed (project required 4 principles, not 5)

Added sections:
  - Engineering Constraints & Tech Stack
  - Development Workflow & Quality Gates
  - Governance

Removed sections:
  - Placeholder 5th principle slot

Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — Constitution Check gate aligns; no
    structural change needed (gates are derived dynamically per principle).
  - ✅ .specify/templates/spec-template.md — Success Criteria already requires
    measurable, technology-agnostic outcomes consistent with Principle IV.
  - ✅ .specify/templates/tasks-template.md — Polish phase already covers perf
    and security; testing tasks remain OPTIONAL per template, but Principle II
    requires them whenever the feature spec touches engine output, scoring, or
    report generation. Reviewers must enforce at the spec stage.
  - ✅ .specify/templates/checklist-template.md — No constitution-specific change
    required for v1.

Follow-up TODOs:
  - None. Ratification date set to today (initial adoption).
-->

# Clean Match Chess Constitution

## Core Principles

### I. Code Quality

All production code MUST be readable, narrowly scoped, and free of dead branches.
Functions SHOULD do one thing; modules SHOULD expose the smallest viable surface.
Public APIs (CLI flags, library functions, HTTP endpoints) MUST have type hints
and a one-line docstring stating purpose, inputs, and failure modes. Linting
(`ruff`) and formatting (`ruff format` / `black`-compatible) MUST pass before
merge; type checking (`mypy --strict` on `src/`) MUST be clean. No `# type: ignore`
without an inline justification. Dependencies are added only with a stated reason
in the PR description; transitive bloat is rejected.

**Rationale**: This project produces evidence that users will attach to formal
abuse reports on chess.com. Sloppy code in the analysis pipeline directly
translates to false accusations or missed cheaters — both are harmful outcomes.

### II. Testing Standards (NON-NEGOTIABLE)

Every signal computation (engine_correlation, CPL, future signals), every
scoring aggregation, and every report-rendering path MUST have unit tests with
fixed PGN/FEN fixtures and pinned Stockfish output. Integration tests MUST cover
the end-to-end CLI flow on at least one known-clean and one known-suspect game
fixture. Tests MUST fail before the corresponding implementation is written
(red → green → refactor). Minimum coverage on `src/cleanmatch/`: **85% line, 80%
branch**. Coverage thresholds are enforced in CI; PRs that drop coverage are
blocked. Flaky tests MUST be quarantined within one working day or deleted —
they are not tolerated as "known issues".

**Rationale**: An audit report is only credible if its underlying calculations
are reproducible bit-for-bit. Untested signal code is unfit to ship.

### III. User Experience Consistency

The CLI is the primary interface through Phase 1–2 and MUST be consistent across
subcommands:
- Exit codes: `0` success, `1` user error, `2` upstream failure
  (chess.com / Stockfish), `3` internal bug.
- Output: `--output json` produces machine-parseable JSON to stdout; human
  output goes to stderr. Default is human-readable.
- Logging: structured (JSON lines) when `--log-format=json`, otherwise pretty.
  Log levels MUST be settable via `--log-level` and `CLEANMATCH_LOG_LEVEL`.
- Naming: subcommands and flags use kebab-case; never mix snake_case in the
  user-facing surface.
- Errors MUST tell the user what failed, why, and what to try next — never a
  raw traceback unless `--debug` is set.

When the Phase 3 web UI lands, these same guarantees (predictable status codes,
JSON-first responses, human-readable error messages) extend to the HTTP API.

**Rationale**: Investigators and moderators using this tool need to script
around it. Surprises in output shape or exit semantics break automation and
erode trust.

### IV. Performance Requirements

Performance budgets are part of acceptance, not an afterthought:
- **Engine analysis**: ≤ 2.0 s wall-clock per ply at depth 18 on the reference
  machine (8-core x86_64, Stockfish 16, single-threaded per game). Batch
  parallelism MUST scale linearly up to `min(cpu_count, games_in_flight)`.
- **Game ingestion**: ≤ 5 s for 100 games from the chess.com public API,
  including rate-limit handling.
- **Report generation**: ≤ 3 s p95 for a 50-game HTML report; ≤ 8 s p95 for the
  PDF variant.
- **Memory**: a single-username analysis of up to 200 games MUST stay under
  1.5 GB RSS.

Every PR that touches `engine/`, `signals/`, `collector/`, or `report/` MUST
either (a) include a benchmark showing the budget is held, or (b) declare a
budget change in the PR description with justification and reviewer sign-off.
Regressions > 10% on any tracked benchmark block merge.

**Rationale**: A fairplay audit that takes ten minutes per suspect will not be
used. Latency is a feature, not a polish item.

## Engineering Constraints & Tech Stack

- **Language**: Python 3.11+. No Python 2 compatibility shims, no `six`.
- **Core dependencies**: `python-chess`, `stockfish` (binary 16+), `httpx`,
  `pydantic` v2, `typer` (CLI), `jinja2` + `weasyprint` (reports). Phase 3 adds
  FastAPI, ARQ, PostgreSQL, Redis, Next.js.
- **Determinism**: Stockfish invocations MUST pin depth, threads, hash, and
  seed where applicable. Any non-determinism in signal output is a bug.
- **Secrets**: No chess.com credentials are required — only the public API is
  used. The codebase MUST refuse to accept passwords or session cookies.
- **Data handling**: Downloaded PGNs and analysis artifacts stay on the local
  filesystem under `~/.cleanmatch/` by default and are never transmitted to
  third parties.

## Development Workflow & Quality Gates

- **Branching**: feature branches per Spec Kit convention (`###-feature-name`).
  `main` is always releasable.
- **Specs first**: non-trivial changes flow through `/speckit-specify` →
  `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`. Drive-by
  refactors > 1 file require a one-paragraph rationale in the PR.
- **Reviews**: at least one reviewer (or self-review checklist for solo work)
  MUST confirm: lint/type clean, tests added or justified absent, perf budget
  held, constitution principles not violated.
- **CI gates** (blocking):
  1. `ruff check` + `ruff format --check`
  2. `mypy --strict src/`
  3. `pytest` with coverage ≥ thresholds in Principle II
  4. Benchmark suite on perf-sensitive paths (Principle IV)
- **Releases**: semantic versioning. CHANGELOG.md updated in the same PR that
  ships user-visible behavior.

## Governance

This constitution supersedes informal practice. When a PR or design conflicts
with a principle, the principle wins unless the constitution is amended in the
same PR (with a Sync Impact Report appended).

Amendments require:
1. A PR editing `.specify/memory/constitution.md` with the new content.
2. A version bump per the rules below.
3. A Sync Impact Report (HTML comment at top of the file) listing changed
   principles, added/removed sections, and templates needing follow-up.
4. Propagation to `.specify/templates/*` where the change alters required
   sections, gates, or task categories.

Versioning policy:
- **MAJOR**: removal or backward-incompatible redefinition of a principle or
  governance rule.
- **MINOR**: new principle or section added; existing principle materially
  expanded.
- **PATCH**: clarifications, wording, typo fixes, non-semantic refinements.

Compliance review: every `/speckit-plan` MUST run the Constitution Check gate
before Phase 0 and again after Phase 1. Violations are tracked in the plan's
Complexity Tracking table with a justification or rejected. Reviewers cite
principle numbers in review comments (e.g., "Violates II — no test for
new signal").

**Version**: 1.0.0 | **Ratified**: 2026-05-23 | **Last Amended**: 2026-05-23
