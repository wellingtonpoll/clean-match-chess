# Contributing to the Forensic Analytics Design System

This document is the **single source of truth** for how the design
system evolves: the canonical workflow for adding a token, registering
a component, extending the lexicon, blocking a new forbidden term, and
filing a legitimate motion exception. Every change MUST follow these
flows so generated artefacts (`adapters/*`), audits, and the
reproducibility manifest stay consistent.

## Semver policy

The design-system package follows strict semver, locked by FR-016:

| Change shape                               | Bump    |
| ------------------------------------------ | ------- |
| Token value tightening / rename            | MAJOR   |
| New token / new component / new audit rule | MINOR   |
| Documentation, fixture-only, refactor      | PATCH   |
| Removing or relaxing an audit              | MAJOR   |
| Easing curve or duration outside locked    | MAJOR   |
| New forbidden term                         | MINOR   |

Every PR that touches `packages/design-system/src/**` MUST update
`packages/design-system/pyproject.toml` `version` field. The bump is
enforced by the CHANGELOG check and by the manifest field test
`packages/report-engine/tests/test_manifest_design_system_version.py`.

## How to add a token (MINOR bump)

1. Edit `src/design_system/tokens/tokens.json` — add the entry under the
   correct namespace (`color.*`, `spacing.*`, `radius.*`, `motion.*`,
   `typography.*`).
2. If it is a colour token, the HSL forbidden-hue rule from
   `audits/palette.py` will catch any red drift; no other guardrail is
   needed.
3. If it is a motion token, the easing curve MUST be `cubic-bezier(0.22,
   1, 0.36, 1)` and the duration MUST be in `[200, 350]` ms. The
   `audits/motion.py` static audit fails on drift.
4. Re-run the adapter compilers:
   ```bash
   uv run python -m design_system.tokens.compile_weasyprint
   uv run python -m design_system.tokens.compile_tailwind
   uv run python -m design_system.tokens.compile_css_vars
   uv run python -m design_system.tokens.compile_framer_motion
   ```
   The golden-file tests under `tests/golden/` will fail if generated
   artefacts drift.
5. Add the token to the relevant component's `tokens_of_record` list in
   `src/design_system/components/catalogue.json` (see "How to add a
   component" below).
6. Bump MINOR in `pyproject.toml` and append an entry to
   `CHANGELOG.md`.

## How to add a component (MINOR bump)

1. Author the entry in `src/design_system/components/catalogue.json`
   with the fields:
   - `name` (kebab-case)
   - `description` (one sentence)
   - `tokens_of_record` (list of namespaced token names)
   - `states` (e.g., `["default", "hover"]`)
   - `surfaces` (subset of `pdf`, `html`, `web`)
   - `accessibility` (object: `contrast_pair`, `aria_role`, `keyboard`)
2. Write an HTML example in `docs/COMPONENTS.md`.
3. Add at least one unit test in
   `tests/unit/test_catalogue_entries.py`.
4. Bump MINOR in `pyproject.toml` and update `CHANGELOG.md`.

## How to extend the lexicon

1. Add the term to `src/design_system/lexicon/entries_en.json` AND
   `entries_pt.json` (parallel structure required).
2. Fields per entry: `term`, `definition`, `context`,
   `alternatives_preferred`, `alternatives_forbidden`.
3. Every `alternatives_forbidden` term MUST appear in
   `tests/fixtures/forbidden-terms/{en,pt}.txt`. The
   `forbidden_alternatives_resolve()` helper enforces this in tests.
4. Refresh `docs/LEXICON.md`.
5. Bump MINOR in `pyproject.toml`.

## How to add a forbidden term

1. Append the row to `tests/fixtures/forbidden-terms/<lang>.txt`. The
   format is TSV: `term<TAB>category<TAB>match_mode`. Categories are
   `accusation`, `verdict`, `slur`. Match modes are `word_boundary` and
   `substring`.
2. Bump the file's `# version:` header.
3. Re-run `uv run pytest packages/design-system` to confirm the
   lexical audit catches the new term in any test corpus.
4. Bump MINOR in `pyproject.toml`.

## How to override motion legitimately

Motion overrides exist for cases where an animation is mandated by
the spec (e.g., progress indicators in the future web surface) but
falls outside the locked easing/duration envelope. The flow:

1. Open a PR adding an entry to
   `src/design_system/audits/motion_overrides.json`. Required fields:
   - `file` (relative path)
   - `selector` (CSS selector inside that file)
   - `reason` (one sentence + spec citation)
   - `reviewer` (GitHub handle)
   - `expiry` (ISO-8601 date, max 90 days from the PR open date)
2. Every override expires; the
   `audits/motion_overrides.check_expiry` helper surfaces expired
   overrides as audit failures.
3. After an override expires, either renew it (new PR, new reviewer)
   or remove it and the animation.

## Definition of done for a design-system PR

- [ ] `uv run ruff check packages/design-system && uv run ruff format --check packages/design-system`
- [ ] `uv run mypy packages/design-system/src`
- [ ] `uv run pytest packages/design-system`
- [ ] Generated adapter files committed
- [ ] `pyproject.toml` version bumped
- [ ] `CHANGELOG.md` updated
- [ ] No new red hue (HSL forbidden-hue rule)
- [ ] No new forbidden term unflagged by audits
