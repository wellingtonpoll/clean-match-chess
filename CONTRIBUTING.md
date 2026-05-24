# Contributing to Clean Match Chess

## Prerequisites

- Python 3.11 or 3.12
- [uv](https://docs.astral.sh/uv/) (package manager)
- [Stockfish 16+](https://stockfishchess.org/download/) binary on `PATH`

## Dev setup

```bash
git clone https://github.com/wellingtonpoll/clean-match-chess.git
cd clean-match-chess
uv sync --all-packages --all-extras
uv run cleanmatch --help   # verify CLI is functional
```

## Running tests

```bash
# Full suite + coverage gate (must stay ≥ 85%)
uv run pytest --cov --cov-fail-under=85

# Single package
uv run pytest packages/analysis-core/tests/

# Only slow/Stockfish tests
uv run pytest -m slow

# Skip slow tests
uv run pytest -m "not slow"
```

## Linting and type-checking

```bash
uv run ruff check .           # lint
uv run ruff format --check .  # format check
uv run ruff format .          # auto-format
uv run mypy                   # strict type checking
```

All four commands must exit 0 before a PR can merge.

## Commit conventions

This project uses [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <short description>

[optional body]
```

Common types: `feat`, `fix`, `refactor`, `docs`, `test`, `ci`, `chore`.

Examples:
```
feat(cli): add --timeout flag to audit-game
fix(heuristics): correct top-3 match rate denominator
ci: pin GitHub Actions to immutable SHAs
```

Keep the subject line under 72 characters.

## PR process

1. Non-trivial changes flow through Spec Kit:
   `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`
2. Create a feature branch: `git checkout -b NNN-short-description`
3. Open a PR against `main` — the PR template will guide you through the checklist.
4. All CI gates must pass (lint, type check, tests, design-system audits).
5. Self-review against the [Constitution](.specify/memory/constitution.md) before
   requesting a merge.

## Constitution

Non-negotiable governance lives in [`.specify/memory/constitution.md`](.specify/memory/constitution.md).
The four principles — code quality, testing (NON-NEGOTIABLE), UX consistency,
performance — apply to every PR. Reviewers cite principle numbers in comments.

## Reporting vulnerabilities

Do not open a public issue for security reports.
See [SECURITY.md](SECURITY.md) for the private disclosure process.
