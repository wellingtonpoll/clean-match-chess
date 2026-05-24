# Feature Specification: Repository Health, Security Hardening & OSS Curation

**Feature Branch**: `003-repo-health-hardening`

**Created**: 2026-05-23

**Status**: Draft

**Input**: User description: "Repository Health, Security Hardening & OSS Curation — closes all gaps identified in the post-audit of clean-match-chess. No user-facing CLI changes: infrastructure, documentation, and developer experience only."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - CI Supply-Chain Hardening (Priority: P1)

A maintainer reviewing a dependency-confusion or tampered-action incident wants
confidence that every GitHub Actions step in this project references an immutable
artefact. They also want every workflow job to run with the minimum permissions
needed, and they want the design-system audit in the `test` job to fail loudly
rather than swallow errors with `|| true`.

**Why this priority**: Supply-chain attacks via mutable GitHub Actions tags are a real
and growing threat. A single compromised action can exfiltrate secrets, tamper with
build artefacts, or inject malicious code. Pinning by SHA and restricting permissions
are the two controls with the highest impact-to-effort ratio. The `|| true` issue
masks real CI failures and is independently dangerous.

**Independent Test**: Can be fully tested by auditing `.github/workflows/ci.yml` for
`uses:` lines — all must match the pattern `owner/action@<40-char hex SHA>` — and
verifying that every `jobs.<job>` block has a `permissions:` key. The `|| true`
removal is verified by grep absence.

**Acceptance Scenarios**:

1. **Given** `.github/workflows/ci.yml` exists, **When** every `uses:` line is inspected,
   **Then** each references a full 40-character SHA (e.g., `actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683`) not a mutable tag.
2. **Given** the CI workflow has four jobs (`test`, `benchmarks`, `design_system_audits`, `sc007_onboarding_log`),
   **When** each job definition is read, **Then** each contains an explicit `permissions:` block listing only the
   permissions required for that job (at minimum `contents: read`).
3. **Given** the `test` job runs design-system audits, **When** those audits fail,
   **Then** the job also fails (i.e., `|| true` is absent from the audit step command).

---

### User Story 2 - README Accuracy & Live Badges (Priority: P1)

A developer visiting the repository on GitHub for the first time wants to know: is
this project active? What is its license? Are the tests passing right now? The current
README shows hardcoded static badges and says "License: TBD" — both undermine trust.

**Why this priority**: The README is the front door of the project. A wrong license
statement is a legal concern and signals neglect. Static badges that show stale numbers
are worse than no badges — they actively mislead. This has zero dependencies on other
stories and is fast to fix.

**Independent Test**: Can be fully tested by opening the repository on GitHub and
verifying: (1) the license section reads "Apache 2.0" with a link to the `LICENSE`
file; (2) all badge images load from live endpoints (GitHub Actions workflow status,
Codecov coverage) and reflect current CI state; (3) the `codecov/codecov-action` step
is present in CI so coverage data is actually uploaded.

**Acceptance Scenarios**:

1. **Given** the README `## License` section, **When** read, **Then** it states
   "Apache 2.0" and links to `LICENSE` (not "TBD").
2. **Given** the CI workflow has passed at least once after this feature lands,
   **When** the README badge row is loaded on GitHub, **Then** the CI badge shows
   "passing" from the live GitHub Actions workflow status endpoint, and the coverage
   badge resolves from `codecov.io` (not a hardcoded string).
3. **Given** `codecov/codecov-action` is added to the `test` job, **When** `pytest
   --cov` runs, **Then** coverage results are uploaded to Codecov and the badge
   reflects the real coverage percentage.

---

### User Story 3 - GitHub Community Health Files (Priority: P2)

A first-time contributor wants to know how to report a bug, open a feature request,
and submit a pull request. Currently there are no issue templates, no PR template,
no root-level CONTRIBUTING.md, and no CHANGELOG.md — the project fails GitHub's
community health checklist.

**Why this priority**: Community health files are table-stakes for a project aspiring
to BigTech-level curation, but they have no impact on existing functionality. They
depend on no other story and can land in any order. P2 because they matter for
contributor experience but not for security or correctness.

**Independent Test**: Can be fully tested by checking GitHub's "Community" tab for the
repository — it should show green checkmarks for Contributing, Code of conduct (via
CONTRIBUTING.md reference), Issue templates, and Pull request template. CHANGELOG.md
existence and content can be verified by reading the file.

**Acceptance Scenarios**:

1. **Given** `.github/ISSUE_TEMPLATE/bug_report.yml` and `.github/ISSUE_TEMPLATE/feature_request.yml`
   exist, **When** a contributor opens a new issue on GitHub, **Then** they are presented
   with structured template forms for bug reports and feature requests.
2. **Given** `.github/PULL_REQUEST_TEMPLATE.md` exists, **When** a contributor opens a
   new pull request, **Then** the PR body is pre-filled with the checklist template.
3. **Given** `CONTRIBUTING.md` exists at the repository root, **When** a contributor
   reads it, **Then** it covers: prerequisites, how to set up the dev environment,
   how to run tests, commit message conventions, and the PR review process.
4. **Given** `CHANGELOG.md` exists at the repository root, **When** read, **Then** it
   follows Keep-a-Changelog format and contains entries for `v0.1.0` (initial CLI MVP)
   and design-system `v1.0.0`.
5. **Given** `.github/CODEOWNERS` exists, **When** a PR is opened touching any file,
   **Then** the maintainer (`@wellingtonpoll`) is automatically requested as a reviewer.

---

### User Story 4 - Automated Dependency Update Scanning (Priority: P2)

A maintainer wants to be notified automatically when a dependency (Python package or
GitHub Action) receives a security patch, so vulnerabilities do not linger unnoticed
between manual reviews.

**Why this priority**: Without automated scanning, security patches in transitive
dependencies are invisible until a researcher publishes a disclosure or a scan is run
manually. Dependabot is free, zero-maintenance, and requires only a config file.

**Independent Test**: Can be fully tested by reading `.github/dependabot.yml` and
verifying both ecosystems are configured. After merging, GitHub's Dependabot page for
the repository will show "Active" status for both configurations.

**Acceptance Scenarios**:

1. **Given** `.github/dependabot.yml` exists, **When** the pip ecosystem entry is read,
   **Then** it targets the `/` directory (workspace root), runs on a weekly schedule,
   and groups dev-dependencies (ruff, mypy, pytest and variants) into a single PR.
2. **Given** `.github/dependabot.yml` exists, **When** the github-actions ecosystem
   entry is read, **Then** it targets `/` and runs on a weekly schedule, so newly
   published SHA-pinned action versions surface as PRs.
3. **Given** the repo has at least one outdated dependency, **When** Dependabot runs
   on its first weekly cycle, **Then** it opens a PR with the update.

---

### User Story 5 - Python Package Hygiene (Priority: P3)

A downstream developer who installs one of the workspace packages in their own project
wants their type checker (mypy, pyright) and IDE (VS Code, PyCharm) to discover the
package's type information automatically, without manual configuration. They also want
`from package import *` to import only the intentional public API.

**Why this priority**: `py.typed` and `__all__` are correctness and ergonomics
improvements with no functional impact on the CLI. They matter only when packages are
consumed externally, which is a future-state concern. P3 is appropriate.

**Independent Test**: Can be fully tested by: (1) verifying a `py.typed` file exists
under `src/<package_name>/` in each of the 6 packages; (2) verifying each
`__init__.py` defines `__all__` with at least one entry; (3) running `uv run mypy`
and confirming it still passes with `--strict`.

**Acceptance Scenarios**:

1. **Given** all 6 packages (`shared-types`, `analysis-core`, `heuristics`,
   `report-engine`, `design-system`, `cleanmatch-cli`), **When** each `src/<pkg>/`
   directory is listed, **Then** a `py.typed` marker file is present in each.
2. **Given** each package's `src/<pkg>/__init__.py`, **When** read, **Then** it
   defines `__all__: list[str]` listing all symbols intended for public consumption.
3. **Given** `py.typed` is added to all packages, **When** `uv run mypy` is executed,
   **Then** it still exits 0 with no new errors.

---

### Edge Cases

- GitHub Actions SHA lookup: some actions may not have a public SHA (private actions).
  Resolution: only pin actions from public repos on GitHub (`github.com`).
- Codecov badge: the badge will show "unknown" until the first successful upload after
  the CI change lands. This is expected and self-resolves on first push.
- `__all__` in packages with complex re-exports: if a package `__init__.py` re-exports
  from submodules, `__all__` must be exhaustive or downstream `import *` will be
  incomplete. Each package's public API surface must be audited before writing `__all__`.
- `dependabot.yml` pip ecosystem with uv workspace: Dependabot supports pip but not uv
  natively. The pip ecosystem targets `pyproject.toml` at `/`. Some workspace packages
  may be missed; this is accepted for now (uv Dependabot support is on their roadmap).

## Requirements *(mandatory)*

### Functional Requirements

**US1 — CI Hardening**

- **FR-001**: Every `uses:` reference in `.github/workflows/*.yml` MUST pin to a full
  40-character commit SHA, not a mutable branch or tag.
- **FR-002**: Every job in every workflow file MUST declare a `permissions:` block
  granting only the permissions required for that job.
- **FR-003**: The `test` job's design-system audit step MUST NOT use `|| true` or any
  equivalent error-suppression operator.

**US2 — README & Badges**

- **FR-004**: The README `## License` section MUST state "Apache 2.0" and link to the
  `LICENSE` file at the repository root.
- **FR-005**: Static CI-status and coverage badge URLs in the README MUST be replaced
  with live endpoints: GitHub Actions workflow status badge and Codecov coverage badge.
  Static tool-enforcement badges (mypy, ruff) MAY remain as shields.io static badges
  since their status is implied by the CI badge passing.
- **FR-006**: The `test` job in CI MUST include a `codecov/codecov-action` step that
  uploads coverage after `pytest --cov`.

**US3 — Community Health Files**

- **FR-007**: `.github/ISSUE_TEMPLATE/bug_report.yml` MUST exist and use GitHub's
  structured issue form format (YAML with `name`, `description`, `body` fields).
- **FR-008**: `.github/ISSUE_TEMPLATE/feature_request.yml` MUST exist in the same format.
- **FR-009**: `.github/PULL_REQUEST_TEMPLATE.md` MUST exist with a checklist covering:
  motivation/context, testing done, and documentation updated.
- **FR-010**: `CONTRIBUTING.md` at the repository root MUST cover: dev environment
  setup (`uv sync`), running tests, commit conventions, and PR process.
- **FR-011**: `CHANGELOG.md` at the repository root MUST follow Keep-a-Changelog
  format and include entries for `v0.1.0` and design-system `v1.0.0`.
- **FR-012**: `.github/CODEOWNERS` MUST assign `@wellingtonpoll` as owner of all files
  (`*`) and optionally add per-directory overrides for `packages/design-system/` and
  `specs/`.

**US4 — Dependabot**

- **FR-013**: `.github/dependabot.yml` MUST configure the `pip` ecosystem targeting
  `/`, with a weekly schedule and a `dev-dependencies` group covering `ruff`, `mypy`,
  and all `pytest*` packages.
- **FR-014**: `.github/dependabot.yml` MUST configure the `github-actions` ecosystem
  targeting `/`, with a weekly schedule.

**US5 — Python Package Hygiene**

- **FR-015**: A `py.typed` marker file (empty, PEP 561) MUST be present in
  `src/<package_name>/` for each of the 6 workspace packages.
- **FR-016**: Each package's `src/<package_name>/__init__.py` MUST define `__all__:
  list[str]` enumerating all public symbols.
- **FR-017**: `uv run mypy` MUST exit 0 with `--strict` after all `py.typed` and
  `__all__` changes are applied.

### Key Entities

- **Workflow file** (`ci.yml`): the single CI definition; changes here affect every
  push and PR.
- **Pinned SHA**: a 40-hex-char immutable reference to a specific commit of a GitHub
  Action; must be kept up-to-date via Dependabot (FR-014).
- **Community health file**: any file in `.github/` or repo root recognised by GitHub
  as contributing to the community profile score.
- **`py.typed` marker**: an empty file at `src/<pkg>/py.typed` that signals PEP 561
  compliance to type checkers.
- **`__all__`**: a Python list of strings in `__init__.py` that defines the public API
  surface for `import *` and IDE auto-complete.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All `uses:` lines in CI reference immutable SHAs — 0 mutable tag
  references remain after the feature lands.
- **SC-002**: GitHub's community health checklist for the repository shows green for:
  Contributing guidelines, Issue templates, Pull request template.
- **SC-003**: The README license section is accurate — 0 instances of "TBD" remain in
  any license-related text.
- **SC-004**: Both Dependabot ecosystems (`pip` and `github-actions`) show "Active" on
  GitHub's Insights → Dependency graph → Dependabot page within 24 hours of merging.
- **SC-005**: `uv run mypy` exits 0 with `--strict` after all package hygiene changes —
  0 new type errors introduced.
- **SC-006**: `uv run pytest --cov --cov-fail-under=85` exits 0 — 0 coverage
  regressions introduced.
- **SC-007**: CI badge on the README reflects live workflow status (not a hardcoded
  string) — verifiable by checking the badge URL is a GitHub Actions endpoint.

## Assumptions

- The Codecov integration requires the repository to be public or connected to a free
  Codecov account at `codecov.io`. It is assumed the maintainer will create this
  account and the `CODECOV_TOKEN` secret in GitHub Settings if required by the action
  version chosen.
- Dependabot's `pip` ecosystem is used (not `uv`) because Dependabot does not yet
  natively support uv workspaces. This covers direct deps in the root `pyproject.toml`;
  individual package `pyproject.toml` files may receive fewer updates.
- CHANGELOG.md entries are written manually for past releases (`v0.1.0` CLI MVP and
  design-system `v1.0.0`) since no automated tooling was in place for those releases.
- GitHub Actions SHA values used in the implementation will be the latest available
  stable versions at the time of implementation. Dependabot will keep them current
  going forward.
- Demo GIF/screenshot for the README is explicitly out of scope for this feature
  (deferred to a future UX/marketing feature).
- Mutation testing (`mutmut`/`cosmic-ray`) is explicitly out of scope for this feature
  (deferred to a future testing-excellence feature).
- All 6 workspace packages are candidates for `py.typed` and `__all__`, including
  `cleanmatch-cli` (which, although an entry point, is still a Python package that
  benefits from PEP 561 compliance).
