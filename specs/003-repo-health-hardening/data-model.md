# Data Model: Repository Health, Security Hardening & OSS Curation

**Feature**: `003-repo-health-hardening`
**Date**: 2026-05-23

---

## Overview

This feature introduces no new domain entities, Pydantic schemas, or runtime data
structures. All changes are to infrastructure files (CI workflows, configuration),
documentation files (README, CHANGELOG, CONTRIBUTING), and Python packaging metadata
(`py.typed`, `__all__`).

---

## Configuration Entities (conceptual, not runtime)

These are file-based configuration structures, documented here for completeness.

### GitHub Actions Workflow Job (ci.yml)

Each job now has an explicit `permissions:` block:

```yaml
jobs:
  <job_name>:
    permissions:
      contents: read   # minimum; only escalate if job explicitly needs write
    steps:
      - uses: <owner>/<action>@<40-char-sha>  # <tag-comment>
```

### Dependabot Configuration (.github/dependabot.yml)

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      dev-dependencies:
        patterns: ["ruff*", "mypy*", "pytest*"]
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
```

### py.typed Marker (PEP 561)

An empty file placed at `src/<package_name>/py.typed`. No schema; its mere existence
signals to type checkers that the package provides inline type information.

### `__all__` Convention

Each top-level `__init__.py` that gains `__all__` follows:

```python
__all__: list[str] = [
    "PublicClass",
    "public_function",
    "PUBLIC_CONSTANT",
]
```

Rules:
- List only symbols intended for external consumers
- Order: classes first, then functions, then constants (alphabetical within each group)
- Private symbols (prefixed with `_`) are excluded by convention
- Sub-module `__init__.py` files are not in scope for this feature

---

## Files Changed Summary

| File | Type | Operation |
|---|---|---|
| `.github/workflows/ci.yml` | YAML | Modify (SHA pin, permissions, remove step) |
| `README.md` | Markdown | Modify (license, badges, codecov step) |
| `.github/dependabot.yml` | YAML | Create |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | YAML | Create |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | YAML | Create |
| `.github/PULL_REQUEST_TEMPLATE.md` | Markdown | Create |
| `.github/CODEOWNERS` | Text | Create |
| `CONTRIBUTING.md` | Markdown | Create |
| `CHANGELOG.md` | Markdown | Create |
| `packages/*/src/*/py.typed` | Empty marker | Create (×6) |
| `packages/*/src/*/__init__.py` | Python | Modify `__all__` (×4 need changes) |
| `apps/cli/src/cleanmatch_cli/__init__.py` | Python | Modify `__all__` |
