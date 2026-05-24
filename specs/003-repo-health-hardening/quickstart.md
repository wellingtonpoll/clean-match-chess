# Quickstart: Repository Health, Security Hardening & OSS Curation

**Feature**: `003-repo-health-hardening`
**Branch**: `003-repo-health-hardening`

---

## Prerequisites

- `uv` installed and workspace synced: `uv sync --all-packages --all-extras`
- GitHub CLI authenticated: `gh auth status`
- Repo remote set to `https://github.com/wellingtonpoll/clean-match-chess` (or SSH equivalent)

---

## Verify US1 — CI Hardening

**Check that all `uses:` lines are SHA-pinned:**

```bash
grep -n "uses:" .github/workflows/ci.yml
# Every line must match pattern: owner/action@<40 hex chars>  # vX.Y.Z
# No line should contain @v1, @v2, @v3, @v4, @main, @master
```

**Check permissions blocks:**

```bash
grep -n "permissions:" .github/workflows/ci.yml
# Should appear once per job (4 jobs = 4 hits minimum)
```

**Check `|| true` absence:**

```bash
grep "|| true" .github/workflows/ci.yml
# Should return nothing
```

---

## Verify US2 — README Accuracy

**Check license section:**

```bash
grep -A2 "## License" README.md
# Should show: [Apache 2.0](LICENSE)
# Must NOT contain "TBD"
```

**Check badge URLs are live (not static):**

```bash
grep "img.shields.io/badge" README.md
# Should return nothing — all static badges replaced with live endpoints
grep "github.com/wellingtonpoll/clean-match-chess/actions" README.md
# Should show the GitHub Actions badge URL
grep "codecov.io" README.md
# Should show the Codecov badge URL
```

**After pushing to main, verify badges resolve:**
Visit `https://github.com/wellingtonpoll/clean-match-chess` and confirm both badges
show live status (not "unknown").

---

## Verify US3 — Community Health Files

**Check all files exist:**

```bash
ls .github/ISSUE_TEMPLATE/    # bug_report.yml, feature_request.yml
ls .github/PULL_REQUEST_TEMPLATE.md
ls .github/CODEOWNERS
ls CONTRIBUTING.md
ls CHANGELOG.md
```

**Check CHANGELOG format:**

```bash
head -20 CHANGELOG.md
# Should show: # Changelog, ## [Unreleased], ## [0.1.0] - YYYY-MM-DD
```

**Check CODEOWNERS format:**

```bash
cat .github/CODEOWNERS
# Should contain: * @wellingtonpoll
```

**After pushing:** Go to `https://github.com/wellingtonpoll/clean-match-chess/community`
and verify green checkmarks for Contributing, Issue templates, Pull request template.

---

## Verify US4 — Dependabot

**Check file exists and is valid:**

```bash
cat .github/dependabot.yml
# Should show pip + github-actions ecosystems, weekly schedule, dev-dependencies group
```

**After merging to main:** Go to
`https://github.com/wellingtonpoll/clean-match-chess/network/updates` and confirm
both ecosystems show "Active".

---

## Verify US5 — Python Package Hygiene

**Check py.typed markers exist:**

```bash
find packages apps -name "py.typed" | sort
# Should list 6 files (one per package)
```

**Check __all__ in top-level __init__.py files:**

```bash
grep -n "__all__" packages/analysis-core/src/analysis_core/__init__.py
grep -n "__all__" packages/heuristics/src/heuristics/__init__.py
grep -n "__all__" packages/report-engine/src/report_engine/__init__.py
grep -n "__all__" packages/design-system/src/design_system/__init__.py
grep -n "__all__" apps/cli/src/cleanmatch_cli/__init__.py
# Each should return a line with __all__ = [...]
```

**Run full test suite to confirm no regressions:**

```bash
uv run mypy
# Exit 0, no new errors

uv run pytest --cov --cov-fail-under=85
# Exit 0, coverage ≥ 85%

uv run ruff check .
uv run ruff format --check .
# Both exit 0
```

---

## Codecov Setup (human step, before US2 CI verification)

1. Go to `https://app.codecov.io/` and sign in with GitHub
2. Add the repository `wellingtonpoll/clean-match-chess`
3. Copy the repository upload token
4. In GitHub: Settings → Secrets and variables → Actions → New repository secret
   - Name: `CODECOV_TOKEN`
   - Value: paste token from Codecov
5. Push a commit and verify the CI `test` job uploads coverage successfully
