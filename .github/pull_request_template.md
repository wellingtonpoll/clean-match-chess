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
- [ ] If `tests/fixtures/forbidden-terms/*.txt` changed: every existing report fixture still passes.

## Heuristic versioning (if applicable)

- [ ] Signals touched have semver bumped (`__signal_version__`) per `docs/heuristics.md` policy.
- [ ] `packages/heuristics/CHANGELOG.md` updated.

## Manual checks

<!-- Any UI / output you visually inspected. -->

-

## Notes for reviewer

<!-- Anything non-obvious; flagged limitations; follow-ups. -->
