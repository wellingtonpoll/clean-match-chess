---
description: "Task list for 003-repo-health-hardening"
---

# Tasks: Repository Health, Security Hardening & OSS Curation

**Input**: Design documents from `specs/003-repo-health-hardening/`

**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, quickstart.md ✅

**Tests**: No new test files required — this feature does not touch signal computation,
scoring, or report rendering. CI gate (`pytest --cov --cov-fail-under=85`) is the
regression check. Spec: Constitution Principle II satisfied.

**Organization**: Tasks grouped by user story. US1 and US2 are P1 (security + trust).
US3 and US4 are P2 (contributor experience). US5 is P3 (downstream hygiene). All
stories are independently implementable — no shared foundational phase required.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on other open tasks)
- **[Story]**: User story tag from spec.md (US1–US5)

---

## Phase 1: Setup

**Purpose**: Verify environment and create directory stubs needed across multiple stories.

- [x] T001 Verify active branch is `003-repo-health-hardening` and `uv sync --all-packages --all-extras` passes cleanly
- [x] T002 Create directory `.github/ISSUE_TEMPLATE/` if it does not yet exist (needed by T011 and T012)

**Checkpoint**: Environment verified, directory stubs ready. All phases can begin.

---

## Phase 2: User Story 1 — CI Supply-Chain Hardening (Priority: P1) 🎯

**Goal**: Every `uses:` line pinned to immutable SHA; every job has `permissions: contents: read`;
`|| true` removed; Codecov upload step added.

**Independent Test**:
```bash
grep "uses:" .github/workflows/ci.yml | grep -v "@[0-9a-f]\{40\}"
# Must return nothing

grep -c "permissions:" .github/workflows/ci.yml
# Must be ≥ 4 (one per job)

grep "|| true" .github/workflows/ci.yml
# Must return nothing
```

- [x] T003 [US1] Pin `actions/checkout` in all occurrences in `.github/workflows/ci.yml` to SHA `11bd71901bbe5b1630ceea73d27597364c9af683` with comment `# v4.2.2`
- [x] T004 [US1] Pin `astral-sh/setup-uv` in all occurrences in `.github/workflows/ci.yml` to SHA `08807647e7069bb48b6ef5acd8ec9567f424441b` with comment `# v8.1.0`
- [x] T005 [US1] Add `permissions:\n  contents: read` block to each of the 4 jobs (`test`, `benchmarks`, `design_system_audits`, `sc007_onboarding_log`) in `.github/workflows/ci.yml`
- [x] T006 [US1] Remove the entire "Design-system audits (when wired)" step (the one with `|| true`) from the `test` job in `.github/workflows/ci.yml`
- [x] T007 [US1] Add `codecov/codecov-action` upload step to the `test` job in `.github/workflows/ci.yml`, pinned to SHA `e79a6962e0d4c0c17b229090214935d2e33f8354` (`# v6.0.1`), with `token: ${{ secrets.CODECOV_TOKEN }}` and `fail_ci_if_error: false`

> ⚠️ **Human prerequisite for SC-007**: Before T007 is verifiable, create a free Codecov account at `codecov.io` (sign in with GitHub), add the repository, copy the upload token, and add it as a GitHub repository secret named `CODECOV_TOKEN` (Settings → Secrets and variables → Actions). The CI step will upload successfully only after this secret exists. The badge will show "unknown" until the first successful upload. See `quickstart.md` for full steps.

**Checkpoint**: CI file fully hardened. Run `grep "uses:" .github/workflows/ci.yml` — every line must include a 40-char SHA.

---

## Phase 3: User Story 2 — README Accuracy & Live Badges (Priority: P1)

**Goal**: README shows Apache 2.0 license, dynamic CI badge, and live Codecov coverage badge.
No static hardcoded badge strings remain.

**Independent Test**:
```bash
grep "TBD" README.md
# Must return nothing

grep "img.shields.io/badge/tests" README.md
grep "img.shields.io/badge/coverage" README.md
# Both must return nothing (static badges replaced)

grep "github.com/wellingtonpoll/clean-match-chess/actions" README.md
grep "codecov.io/gh/wellingtonpoll" README.md
# Both must return something (live endpoints present)
```

- [x] T008 [US2] Replace the 6 static `shields.io/badge` badge lines in `README.md` with 5 live-endpoint badges: GitHub Actions CI status, Codecov coverage, mypy (static OK), ruff (static OK), Apache 2.0 license (static OK). See plan.md Phase 2 for exact badge URLs.
- [x] T009 [US2] Replace `## License\n\nTBD.` with `## License\n\n[Apache 2.0](LICENSE)` in `README.md`
- [x] T010 [US2] Add `**Requirements**: Python 3.11+, [Stockfish 16+](https://stockfishchess.org/download/)` line after the quickstart code block in `README.md`

**Checkpoint**: `grep "TBD" README.md` returns nothing. Badge row contains live endpoints.

---

## Phase 4: User Story 3 — GitHub Community Health Files (Priority: P2)

**Goal**: Bug report template, feature request template, PR template, CONTRIBUTING.md,
CHANGELOG.md, and CODEOWNERS all present and well-formed.

**Independent Test**:
```bash
ls .github/ISSUE_TEMPLATE/bug_report.yml
ls .github/ISSUE_TEMPLATE/feature_request.yml
ls .github/PULL_REQUEST_TEMPLATE.md
ls .github/CODEOWNERS
ls CONTRIBUTING.md
ls CHANGELOG.md
head -5 CHANGELOG.md  # must start with "# Changelog"
```

- [x] T011 [P] [US3] Create `.github/ISSUE_TEMPLATE/bug_report.yml` as a GitHub structured issue form (YAML with `name: Bug report`, `description`, `labels: ["bug"]`, and `body` containing: Summary textarea, Steps to Reproduce textarea, Expected vs Actual textarea, Version input, OS dropdown [Linux/macOS/Windows], PGN snippet textarea [not required])
- [x] T012 [P] [US3] Create `.github/ISSUE_TEMPLATE/feature_request.yml` as a GitHub structured issue form (YAML with `name: Feature request`, `description`, `labels: ["enhancement"]`, and `body` containing: Problem textarea, Proposed Solution textarea, Alternatives Considered textarea, Additional Context textarea)
- [x] T013 [P] [US3] Create `.github/PULL_REQUEST_TEMPLATE.md` with a checklist covering: linked issue, change type (bug fix / feature / refactor / docs / infra / chore), tests added or justified absent, `uv run mypy` passes, `uv run ruff check .` passes, `uv run pytest --cov` passes, docs updated if needed
- [x] T014 [P] [US3] Create `CONTRIBUTING.md` at repo root with sections: Prerequisites (Python 3.11+, uv, Stockfish 16+), Dev Setup (`uv sync --all-packages --all-extras`), Running Tests (`uv run pytest --cov`), Linting & Type-checking (`uv run ruff check .` and `uv run mypy`), Commit Conventions (Conventional Commits style used in this repo), PR Process (feature branch → spec → PR with template → review), Constitution reference (link to `.specify/memory/constitution.md`)
- [x] T015 [P] [US3] Create `CHANGELOG.md` at repo root in Keep-a-Changelog format with: `# Changelog` header, `## [Unreleased]` section, `## [1.0.0-design-system] - 2026-05-23` section listing Forensic Analytics Design System additions (palette/typography/motion/lexical audits, CI enforcement, 4-audit suite), `## [0.1.0] - 2026-05-23` section listing MVP CLI auditor additions (PGN ingest, Stockfish pipeline, 5 heuristic signals, HTML/PDF/JSON reports, reproducibility manifest)
- [x] T016 [P] [US3] Create `.github/CODEOWNERS` with `* @wellingtonpoll` as the global rule, plus optional per-directory entries for `packages/design-system/ @wellingtonpoll` and `specs/ @wellingtonpoll`

**Checkpoint**: All 6 community health files exist. `head -5 CHANGELOG.md` shows Keep-a-Changelog header.

---

## Phase 5: User Story 4 — Automated Dependency Updates (Priority: P2)

**Goal**: Dependabot active for pip and github-actions ecosystems, weekly schedule,
dev-dependencies grouped.

**Independent Test**:
```bash
cat .github/dependabot.yml
# Must show: version: 2, pip ecosystem at /, github-actions ecosystem at /, weekly schedule
grep "dev-dependencies" .github/dependabot.yml
# Must show the grouped pattern with ruff*, mypy*, pytest*
```

- [x] T017 [US4] Create `.github/dependabot.yml` with `version: 2`, pip ecosystem (`directory: "/"`, `schedule: interval: "weekly"`, `groups.dev-dependencies.patterns: ["ruff*", "mypy*", "pytest*"]`), and github-actions ecosystem (`directory: "/"`, `schedule: interval: "weekly"`). See research.md US4 section for exact YAML.

**Checkpoint**: `cat .github/dependabot.yml` shows both ecosystems with weekly schedule.

---

## Phase 6: User Story 5 — Python Package Hygiene (Priority: P3)

**Goal**: All 6 packages have `py.typed` PEP 561 marker files; all top-level
`__init__.py` files define `__all__`.

**Independent Test**:
```bash
find packages apps -name "py.typed" | sort
# Must list 6 files

grep -l "__all__" \
  packages/analysis-core/src/analysis_core/__init__.py \
  packages/heuristics/src/heuristics/__init__.py \
  packages/report-engine/src/report_engine/__init__.py \
  packages/design-system/src/design_system/__init__.py \
  apps/cli/src/cleanmatch_cli/__init__.py
# Must list all 5 files

uv run mypy
# Must exit 0 (no new errors)
```

### py.typed markers (all parallelizable — 6 independent empty files)

- [x] T018 [P] [US5] Create empty file `packages/analysis-core/src/analysis_core/py.typed` (PEP 561 marker)
- [x] T019 [P] [US5] Create empty file `packages/design-system/src/design_system/py.typed` (PEP 561 marker)
- [x] T020 [P] [US5] Create empty file `packages/heuristics/src/heuristics/py.typed` (PEP 561 marker)
- [x] T021 [P] [US5] Create empty file `packages/report-engine/src/report_engine/py.typed` (PEP 561 marker)
- [x] T022 [P] [US5] Create empty file `packages/shared-types/src/shared_types/py.typed` (PEP 561 marker)
- [x] T023 [P] [US5] Create empty file `apps/cli/src/cleanmatch_cli/py.typed` (PEP 561 marker)

### `__all__` additions (all parallelizable — different files)

- [x] T024 [P] [US5] Add `__all__: list[str]` to `packages/analysis-core/src/analysis_core/__init__.py` exporting: `build_manifest`, `run_single_game`, `run_username_batch`, `DEFAULT_DESIGN_SYSTEM_VERSION` (import these from their submodules in the same edit)
- [x] T025 [P] [US5] Add `__all__: list[str]` to `packages/heuristics/src/heuristics/__init__.py` exporting symbols from `heuristics.registry`: `RegisteredSignal`, `register`, `unregister`, `snapshot`, `versions`, `lookup` (import from `heuristics.registry` in the same edit)
- [x] T026 [P] [US5] Read `packages/report-engine/src/report_engine/bundle.py`, `render_html.py`, `render_json.py`, `render_pdf.py` to identify all public functions/classes, then add `__all__: list[str]` to `packages/report-engine/src/report_engine/__init__.py` importing and exporting those symbols
- [x] T027 [P] [US5] Read `packages/design-system/src/design_system/version.py`, `manifest.py`, and `audits/__init__.py` to identify public symbols, then expand `__all__` in `packages/design-system/src/design_system/__init__.py` beyond the current `["__version__"]` to include `current_version` and any public audit entry points
- [x] T028 [P] [US5] Add `__all__: list[str] = ["app"]` to `apps/cli/src/cleanmatch_cli/__init__.py`, importing `app` from `cleanmatch_cli.main`

**Checkpoint**: `find packages apps -name "py.typed" | wc -l` returns 6. `uv run mypy` exits 0.

---

## Phase 7: Polish & Verification

**Purpose**: Full regression check and quickstart validation for all 5 stories.

- [x] T029 Run `uv run mypy` and confirm exit 0 — no type errors introduced by py.typed or `__all__` changes
- [x] T030 Run `uv run pytest --cov --cov-fail-under=85` and confirm exit 0 — no coverage regression
- [x] T031 [P] Run `uv run ruff check . && uv run ruff format --check .` and confirm both exit 0
- [x] T032 Run all verification commands from `specs/003-repo-health-hardening/quickstart.md` for US1–US5 and confirm each passes

**Checkpoint**: All quality gates pass. Feature ready for merge.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (US1)**: Depends only on Phase 1
- **Phase 3 (US2)**: Logically follows Phase 2 (Codecov step must be in CI before badge is useful, but README changes are standalone — can start in parallel)
- **Phase 4 (US3)**: Depends only on Phase 1 — parallel with Phases 2 and 3
- **Phase 5 (US4)**: Depends only on Phase 1 — parallel with Phases 2, 3, and 4
- **Phase 6 (US5)**: Depends only on Phase 1 — parallel with Phases 2–5
- **Phase 7 (Polish)**: Depends on completion of all phases 2–6

### User Story Dependencies

- **US1 (P1)**: Independent — start after Setup
- **US2 (P1)**: Independent for README content; Codecov badge only meaningful after US1 merges to main
- **US3 (P2)**: Fully independent — all 6 files in different locations
- **US4 (P2)**: Fully independent — single file
- **US5 (P3)**: Fully independent — non-overlapping files

### Within Each Story

- US1: T003/T004 (SHA pins) must precede T005 (permissions) only by convention; all can be done in one ci.yml edit pass
- US3: T011–T016 are fully parallel (different files)
- US5: T018–T023 (py.typed) are fully parallel; T024–T028 (`__all__`) are fully parallel; py.typed and `__all__` tasks are also independent of each other

---

## Parallel Execution Examples

### Phase 2 (US1) — Single file, sequential edit pass

```
T003 → T004 → T005 → T006 → T007  (all in one ci.yml edit session)
```

### Phase 4 (US3) — All parallel

```
T011 [bug_report.yml]
T012 [feature_request.yml]    ← all 6 launch simultaneously
T013 [PULL_REQUEST_TEMPLATE]
T014 [CONTRIBUTING.md]
T015 [CHANGELOG.md]
T016 [CODEOWNERS]
```

### Phase 6 (US5) — py.typed fully parallel, then __all__ fully parallel

```
# Batch 1: py.typed markers
T018 T019 T020 T021 T022 T023   ← 6 parallel empty file creates

# Batch 2: __all__ additions (no dependency on Batch 1, but logical grouping helps)
T024 T025 T026 T027 T028        ← 5 parallel __init__.py edits
```

---

## Implementation Strategy

### MVP First (US1 — Highest Security Impact)

1. Complete Phase 1 (Setup)
2. Complete Phase 2 (US1 — CI Hardening) — highest impact, lowest risk
3. **STOP and VALIDATE**: `grep "uses:" ci.yml | grep -v "@[0-9a-f]\{40\}"` returns nothing
4. Optionally commit and push for immediate security benefit

### Incremental Delivery

1. Setup → US1 (P1, security) → US2 (P1, trust) → merge to main
2. US3 (P2, community) + US4 (P2, dependabot) → merge to main
3. US5 (P3, hygiene) → merge to main

### Solo Strategy (recommended)

With a single implementer, prioritize by risk:

1. Phase 2 (US1) — security, deploy fast
2. Phase 3 (US2) — trust, fast edit
3. Phase 4 (US3) — parallelise with Agent tool (6 independent files)
4. Phase 5 (US4) — single file, 2 minutes
5. Phase 6 (US5) — parallelise py.typed batch, then `__all__` batch

---

## Notes

- `[P]` = different files, no blocking dependencies — safe to execute in parallel
- `[Story]` label maps each task to its acceptance criteria in spec.md
- US5 `__all__` tasks (T026, T027) require reading submodule files first — do not infer symbol names without reading source
- After T007 (Codecov step), a human must create the Codecov account and `CODECOV_TOKEN` secret before the badge resolves (see quickstart.md)
- T002 is idempotent — `mkdir -p` is safe to re-run
- All tasks can be committed incrementally; no task leaves the repo in a broken state
