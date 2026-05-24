# Research: Repository Health, Security Hardening & OSS Curation

**Feature**: `003-repo-health-hardening`
**Date**: 2026-05-23

---

## US1 — GitHub Actions SHA Pinning

### Decision: Pin every `uses:` to full 40-char commit SHA

**Rationale**: Mutable tags (`@v4`) can be force-pushed by the upstream author or by
a compromised maintainer account. Pinning to the immutable commit SHA ensures the exact
byte content of the action runs, regardless of what the tag points to at execution time.

**Current action versions and their pinned SHAs** (verified via GitHub API, 2026-05-23):

| Action (current ref) | Upgrade to | Commit SHA (40-char) |
|---|---|---|
| `actions/checkout@v4` | `v4.2.2` | `11bd71901bbe5b1630ceea73d27597364c9af683` |
| `astral-sh/setup-uv@v3` | `v8.1.0` | `08807647e7069bb48b6ef5acd8ec9567f424441b` |
| `codecov/codecov-action` (new) | `v6.0.1` | `e79a6962e0d4c0c17b229090214935d2e33f8354` |

**Convention**: always append a human-readable comment with the tag for readability:
```yaml
uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2
```

**Dependabot keeps SHAs current**: once `.github/dependabot.yml` is configured for
`github-actions`, Dependabot opens PRs when upstream releases new versions, updating
both the SHA and the comment.

### Decision: Minimum permissions per job

**Rationale**: GitHub Actions tokens inherit broad repository permissions by default
(`contents: write`, `packages: write`). Least-privilege grants reduce the blast radius
if a malicious action step exfiltrates the token.

Minimum viable permissions per job in `ci.yml`:

| Job | Required permissions |
|---|---|
| `test` | `contents: read` |
| `benchmarks` | `contents: read` |
| `design_system_audits` | `contents: read` |
| `sc007_onboarding_log` | `contents: read` |

Codecov upload (added to `test`) does not require elevated permissions — `codecov-action`
uses a token from secrets, not the workflow token. So `contents: read` remains sufficient.

### Decision: Remove `|| true` from design-system audit step

The `test` job currently has:
```yaml
uv run pytest -m "audit_palette or ..." --no-cov || true
```
This silences failures. The `design_system_audits` job already runs the same tests
enforced (no `|| true`). The step in `test` should be removed entirely to avoid
duplication and confusion. The enforced job is the gate.

**Alternatives considered**:
- Replace with `continue-on-error: true` → same problem, silences failures
- Remove the step entirely from `test` → cleanest; `design_system_audits` is the gate

**Resolution**: Remove the design-system audit step from the `test` job entirely.
The `design_system_audits` job (which runs after `test`) is the enforced gate.

---

## US2 — README & Dynamic Badges

### Decision: Use GitHub Actions workflow badge + Codecov for coverage

**Badge URLs** (using repo path `wellingtonpoll/clean-match-chess`):

```markdown
[![CI](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml/badge.svg)](https://github.com/wellingtonpoll/clean-match-chess/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/wellingtonpoll/clean-match-chess/branch/main/graph/badge.svg)](https://codecov.io/gh/wellingtonpoll/clean-match-chess)
```

**Rationale**: GitHub Actions badge is zero-config — derived from the workflow file,
always reflects the last run on `main`. Codecov requires:
1. Free account at `codecov.io` (sign in with GitHub)
2. Add `CODECOV_TOKEN` as a repository secret in GitHub Settings
3. `codecov/codecov-action` step after `pytest --cov` in CI

**Alternatives considered**:
- Coveralls.io: similar to Codecov but less popular in Python ecosystem
- Keep static badge: contradicted by US2 acceptance criteria

### Decision: Fix license section

Replace `## License\n\nTBD.` with:
```markdown
## License

[Apache 2.0](LICENSE)
```

---

## US3 — GitHub Community Health Files

### Decision: Use GitHub structured issue form format (YAML) for templates

**Rationale**: GitHub's form-based issue templates (`.yml` extension) produce a
structured UI with dropdowns, checkboxes, and validated fields — significantly better
contributor experience than the older markdown-based templates.

**Format reference**: Each template needs `name`, `description`, `labels`, and `body`
fields. The `body` is a list of form elements (`input`, `textarea`, `dropdown`,
`checkboxes`, `markdown`).

### Decision: Keep-a-Changelog format for CHANGELOG.md

**Rationale**: Keep-a-Changelog (`keepachangelog.com`) is the most widely adopted
changelog format in open source. It uses `## [Unreleased]` + `## [X.Y.Z] - YYYY-MM-DD`
sections with sub-categories: `Added`, `Changed`, `Fixed`, `Removed`, `Security`.

**Initial entries to document**:
- `[0.1.0] - 2026-05-23` — MVP CLI auditor (features 001): PGN ingest, Stockfish
  analysis pipeline, 5 heuristic signals, HTML/PDF/JSON reports, 103 tasks complete
- `[1.0.0-design-system] - 2026-05-23` — Forensic Analytics Design System (feature 002):
  palette, typography, motion, and lexical audits enforced in CI

Note: The design system version is documented as a separate entry since it tracks its
own `1.0.0` version independently of the CLI.

### Decision: CODEOWNERS assigns all files to @wellingtonpoll

Simple rule: `* @wellingtonpoll` with optional overrides for critical areas.

---

## US4 — Dependabot

### Decision: pip ecosystem at `/`, weekly, dev-deps grouped

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      dev-dependencies:
        patterns:
          - "ruff*"
          - "mypy*"
          - "pytest*"
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

**Known limitation**: Dependabot's pip ecosystem reads `pyproject.toml` at the specified
directory. With a uv workspace, it may not discover all workspace member dependencies.
This is accepted — the root `pyproject.toml` covers dev deps, which are the most
security-critical. Dependabot support for uv is on Dependabot's roadmap.

---

## US5 — Python Package Hygiene

### Decision: py.typed marker in all 6 packages

**Spec**: PEP 561 requires an empty `py.typed` file at the package root
(alongside `__init__.py`) to signal that the package provides type information.

**Placement** (6 files to create):
```
packages/analysis-core/src/analysis_core/py.typed
packages/design-system/src/design_system/py.typed
packages/heuristics/src/heuristics/py.typed
packages/report-engine/src/report_engine/py.typed
packages/shared-types/src/shared_types/py.typed        # may already exist — check
apps/cli/src/cleanmatch_cli/py.typed
```

**Each package's pyproject.toml needs**: `[tool.setuptools.package-data]` or equivalent
uv/flit/hatchling config to include `py.typed` in the distribution. With uv + hatchling,
the standard approach is adding `"py.typed"` to `include` patterns.

### Decision: `__all__` in top-level package `__init__.py` only

FR-016 targets each package's top-level `__init__.py`. Sub-module `__init__.py` files
(e.g., `analysis_core/engine/__init__.py`) are implementation details — their `__all__`
is optional and left to a future refactor.

**Current `__all__` status per package**:

| Package | Status | Action needed |
|---|---|---|
| `shared_types` | ✅ Complete (33 symbols) | None |
| `heuristics/scoring` | ✅ Complete (6 symbols) | None |
| `design_system` | ⚠️ Only `__version__` | Expand with manifest, audits |
| `analysis_core` | ❌ Missing | Add with pipeline, manifest symbols |
| `heuristics` (top) | ❌ Missing | Add with signal modules, registry |
| `report_engine` | ❌ Missing | Add with bundle, render functions |
| `cleanmatch_cli` | ❌ Missing | Add with `app` (Typer app, minimal) |

### Public API surface per package (derived from module inspection)

**analysis_core** — public symbols:
- `build_manifest` (from `manifest.py`)
- `run_single_game`, `run_username_batch` (from `pipeline/run.py`)
- `DEFAULT_DESIGN_SYSTEM_VERSION` (from `pipeline/run.py`)

**heuristics** (top-level registry) — public symbols:
- `RegisteredSignal`, `register`, `unregister`, `snapshot`, `versions`, `lookup`
  (from `registry.py`)

**report_engine** — public symbols:
- `create_bundle` (from `bundle.py` — exact name to verify at implementation)
- `render_html`, `render_json`, `render_pdf` (from render_*.py — exact names to verify)

**design_system** (expand from `__version__` only) — add:
- `current_version` (from `version.py`)
- `__version__`
- Audit runner exports from `audits/` subpackage

**cleanmatch_cli** — entry point; public API is minimal:
- `app` (the Typer application instance)

**Note**: Exact symbol names for `report_engine` and `design_system` must be verified
by reading the module files during implementation. The list above is a best-effort
survey from the module structure.
