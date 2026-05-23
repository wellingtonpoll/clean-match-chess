## Summary

<!-- 1-3 bullets describing what this PR changes and why. -->

-
-

## Constitution check (.specify/memory/constitution.md)

- [ ] **Principle I (Code Quality):** ruff + ruff format + mypy --strict all green; no new `# type: ignore` without a one-line justification.
- [ ] **Principle II (Testing — NON-NEGOTIABLE):** every new public surface has a test; coverage stays ≥85% line / ≥80% branch on `packages/*/src/`.
- [ ] **Principle III (UX Consistency):** CLI exit codes 0/1/2/3 honoured; `--output` / `--log-format` / `--log-level` consistent; kebab-case subcommands; errors actionable.
- [ ] **Principle IV (Performance Requirements):** if this PR touches `packages/analysis-core/`, `packages/heuristics/`, or `packages/report-engine/`, attach a benchmark result OR declare a budget change in this PR description with sign-off.

## Brand / forbidden-vocabulary

- [ ] Rendered artefacts pass the lexical audit (`uv run pytest -m audit_lexical` or `python -m design_system.audits.lexical`).
- [ ] If `tests/fixtures/forbidden-terms/*.txt` changed: every existing report fixture still passes; the forbidden-terms file diff is intentional and reviewed.

## Design system (feature 002)

- [ ] All four design-system audits ran clean
      (`uv run pytest -m "audit_palette or audit_typography or audit_motion or audit_lexical"`).
- [ ] Version bump categorisation declared (pick one):
      - [ ] PATCH — docs / fixtures / refactor only
      - [ ] MINOR — new token, component, lexicon entry, or forbidden term
      - [ ] MAJOR — removed/relaxed audit, changed easing/duration envelope, removed lexicon term
      - [ ] None — no design-system surface touched
- [ ] If touched: `packages/design-system/pyproject.toml` version updated.
- [ ] If touched: `packages/design-system/CHANGELOG.md` updated.
- [ ] If adapter files regenerated: committed artefacts under
      `packages/design-system/adapters/**` match the compiler output
      (golden-file tests will confirm).
- [ ] Motion overrides (if added): expiry ≤ 90 days, reviewer + reason filled in.

## Heuristic versioning (if applicable)

- [ ] Signals touched have semver bumped (`__signal_version__`) per `docs/heuristics.md` policy.
- [ ] `packages/heuristics/CHANGELOG.md` updated.

## Manual checks

<!-- Any UI / output you visually inspected. -->

-

## Notes for reviewer

<!-- Anything non-obvious; flagged limitations; follow-ups. -->
