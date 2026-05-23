# SC-007 Onboarding Log

This protocol operationalises **SC-007**: "A new contributor with no
prior exposure to the design system can land a passing PR on their
first attempt." The metric is the rolling rate at which new
contributors clear all four audits on their *first* commit, before
any maintainer review push. This document is the canonical
methodology; results live in
[`SC007_RESULTS.md`](SC007_RESULTS.md). The doc itself MUST pass the
lexical audit.

## Definitions

### Onboarding event

A pull request is an "onboarding event" iff **all** of the following
hold:

1. The PR carries the GitHub label `onboarding-event`.
2. The PR author has fewer than three prior commits authored to
   `packages/design-system/**` OR `packages/report-engine/**` on the
   `main` branch.
3. The PR touches at least one file under one of those two paths.

Maintainers apply the label during triage; the CI step described
below also detects mis-labelled candidates and posts a comment.

### First-commit pass criterion

The PR's *first* push (the commit that opens the PR, before any
amendments, force-pushes, or maintainer pushes) MUST clear:

- `audit_palette` (Track A + Track C on rendered fixtures)
- `audit_typography` (CSS + role-marker checks)
- `audit_motion` (static CSS envelope)
- `audit_lexical` (en + pt)

If the first push has any audit failure, the PR is recorded as a
fail even if a later push lands clean.

## Rolling passing-rate target

- Window: most recent **three** onboarding events.
- Target: ≥ 80 % first-push pass rate (i.e., at least 3 of 3 OR 4
  of 5 in the rolling window).
- Below target → trigger a docs review: the maintainer who applied
  the label opens an issue under
  `specs/002-design-system/research.md` listing the first-push
  failure modes.

## Tally template

Append every onboarding event to
[`SC007_RESULTS.md`](SC007_RESULTS.md) using the schema:

```markdown
| Date       | Contributor       | PR URL                            | First-push result |
| ---------- | ----------------- | --------------------------------- | ----------------- |
| YYYY-MM-DD | @githubhandle     | https://github.com/.../pull/N     | PASS / FAIL       |
```

A short "notes" line below each row may capture which audit failed
and the corrective edit the contributor made.

## CI wiring

Add the following job stub to `.github/workflows/ci.yml` (skeleton —
the row-append helper script is deferred to a follow-up PR; the
job's role today is to *detect* the label, run the four audits with
hard failure on the first push, and emit a structured log line the
follow-up script will parse):

```yaml
sc007_onboarding_log:
  if: contains(github.event.pull_request.labels.*.name, 'onboarding-event')
  runs-on: ubuntu-latest
  needs: design_system_audits
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    - uses: astral-sh/setup-uv@v3
      with:
        version: "0.11.5"
    - run: uv python install 3.11
    - run: uv sync --all-packages --all-extras
    - name: Run the four locked audits (first push only)
      run: |
        if [ "${{ github.event.pull_request.commits }}" -ne 1 ]; then
          echo "SC007: skipping — PR has more than one push"
          exit 0
        fi
        uv run pytest \
          packages/design-system/tests/ \
          -m "audit_palette or audit_typography or audit_motion or audit_lexical" \
          --no-cov
    - name: Emit structured log line
      if: always()
      run: |
        printf 'SC007_EVENT date=%s author=%s pr=%s result=%s\n' \
          "$(date -u +%Y-%m-%d)" \
          "${{ github.event.pull_request.user.login }}" \
          "${{ github.event.pull_request.html_url }}" \
          "${{ job.status }}"
```

The follow-up script (deferred; tracked separately) will:

1. Scan recent CI run logs for `SC007_EVENT` lines.
2. Append a row to `SC007_RESULTS.md`.
3. Recompute the rolling pass rate and post a sticky PR comment.

## When to re-evaluate the protocol

- Whenever the rolling rate drops below the 80 % target.
- Before every MAJOR release of the design system.
- Whenever the structure of `docs/CONTRIBUTING.md` changes
  significantly enough that a fresh contributor would land in a
  different flow.

## Cross-feature references

- Contributor flow: [`docs/CONTRIBUTING.md`](CONTRIBUTING.md)
- Audits enforced in CI: `.github/workflows/ci.yml` job
  `design_system_audits`
- Lexical audit (used for ensuring this doc itself stays clean):
  `src/design_system/audits/lexical.py`
