---
description: "Task list for feature 002-design-system (Forensic Analytics Design System)"
---

# Tasks: Forensic Analytics Design System

**Input**: Design documents from `/specs/002-design-system/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: REQUIRED. Constitution Principle II is NON-NEGOTIABLE — every
audit, every adapter compile step, every token-loader rule, and every
cross-feature contract gets red-first unit and golden-file tests.
Coverage gate: 85% line / 80% branch on
`packages/design-system/src/`.

**Organization**: Tasks grouped by user story (US1…US3 from `spec.md`).

**Cross-feature impact**: this feature edits feature 001-fairplay-analysis
in three places: extend `packages/shared-types` (`ReproducibilityManifest`
adds `design_system_version`), wire `packages/report-engine` to consume
the design-system, and extend `tests/fixtures/forbidden-terms/{en,pt}.txt`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Parallelizable (different files, no incomplete dependency).
- **[Story]**: User story tag (US1, US2, US3); Setup, Foundational,
  Polish phases carry none.

## Path Conventions

Monorepo (Python uv workspace) — design-system lives at
`packages/design-system/`. Cross-feature edits target
`packages/{shared-types,report-engine}/` and
`tests/fixtures/forbidden-terms/`.

---

## Phase 1: Setup (Package Bootstrap)

- [x] T001 Create `packages/design-system/` skeleton: `pyproject.toml`, `src/design_system/__init__.py`, `src/design_system/{tokens,components,lexicon,audits,version,manifest}.py` placeholders, `adapters/{weasyprint,tailwind,shadcn,framer-motion}/`, `benchmarks/`, `tests/{unit,fixtures,golden}/`
- [x] T002 [P] Add `packages/design-system` to the root `pyproject.toml` workspace members list
- [x] T003 [P] Declare runtime dependencies in `packages/design-system/pyproject.toml`: `pydantic>=2`, `tinycss2`, `colormath`, `pdfminer.six`, `selectolax`, plus dev deps `pytest`, `pytest-cov`, `pytest-benchmark`
- [x] T004 [P] Add `packages/design-system/src/design_system/version.py` exporting `__version__ = "0.1.0"` sourced via `importlib.metadata`
- [x] T005 [P] Add fixture directories `packages/design-system/tests/fixtures/{tokens-valid,tokens-invalid,images,lexicon}/` with placeholder `.gitkeep`
- [x] T006 [P] Update root `pyproject.toml` `[tool.ruff]` and `[tool.mypy]` to include `packages/design-system/src/` in source paths
- [x] T007 [P] Update `.github/workflows/ci.yml` so it runs the design-system tests + audits via `uv run pytest -m "audit_palette or audit_typography or audit_motion or audit_lexical"`

**Checkpoint**: `uv sync` resolves the new package; `uv run pytest packages/design-system` is empty-green.

---

## Phase 2: Foundational (Blocking Prerequisites)

### Token entities (data-model.md → `packages/design-system/src/design_system/tokens/`)

- [x] T008 [P] Write failing unit tests for the Pydantic v2 loader covering: name regex, `^#[0-9A-F]{6}$` uppercase hex, forbidden-hue rule (HSL hue 350–360° ∪ 0–20° at S>30%), locked spacing set, locked radius bounds, locked motion duration bounds in `packages/design-system/tests/unit/test_token_loader.py`
- [x] T009 [P] [Foundational] Write failing tests for `TokenFile` schema validation against `tests/fixtures/tokens-invalid/` (one fixture per violation: red token, off-spacing, bad-easing, missing-required) in `packages/design-system/tests/unit/test_token_validation.py`
- [x] T010 Implement `packages/design-system/src/design_system/tokens/loader.py` — Pydantic `TokenFile`, `DesignToken`, polymorphic `TokenValue` (Colour/Typography/Shadow/Motion), forbidden-hue check (turns T008–T009 green)
- [x] T011 [P] Implement `packages/design-system/src/design_system/tokens/types.py` — supporting enums (`TokenCategory`, `RiskLevel`) and polymorphic value classes

### Lexicon + forbidden-terms

- [x] T012 [P] [Foundational] Write failing unit tests for `Lexicon` + `LexiconEntry` schema in `packages/design-system/tests/unit/test_lexicon.py`
- [x] T013 [P] [Foundational] Write failing unit tests for `ForbiddenTermsFile` TSV parser (skip `#`-comments, three-column rows, category + match-mode enums) in `packages/design-system/tests/unit/test_forbidden_terms.py`
- [x] T014 Implement `packages/design-system/src/design_system/lexicon/lookup.py` exposing `load_lexicon(lang) -> Lexicon`, `load_forbidden_terms(lang) -> ForbiddenTermsFile`, and `forbidden_alternatives_resolve(entry) -> bool` (turns T012-T013 green)

### Component catalogue + risk treatments

- [x] T015 [P] [Foundational] Write failing unit tests asserting every `Component.tokens_of_record` token name resolves in the loaded `TokenFile` in `packages/design-system/tests/unit/test_components.py`
- [x] T016 [P] Implement `packages/design-system/src/design_system/components/catalogue.py` (loader + access helpers)
- [x] T017 [P] Implement `packages/design-system/src/design_system/components/risk_treatments.py` — three locked `RiskTreatment` constants (LOW/MEDIUM/HIGH) per data-model §8 with the locked amber `#F4B41F` for MEDIUM, signal `#F4D21F` for HIGH

### Audit report core

- [x] T018 [P] [Foundational] Write failing unit tests for `AuditReport` + `AuditFinding` Pydantic models + JSON serialisation in `packages/design-system/tests/unit/test_audit_report.py`
- [x] T019 [P] Implement `packages/design-system/src/design_system/audits/report.py` — `AuditReport`, `AuditFinding`, `TrackResult` dataclasses + JSON serializer (turns T018 green)
- [x] T020 [P] Implement `packages/design-system/src/design_system/audits/pytest_plugin.py` registering marks `audit_palette`, `audit_typography`, `audit_motion`, `audit_lexical`

### Cross-feature: extend feature 001 shared-types

- [x] T021 [Foundational] Write failing unit test in `packages/shared-types/tests/test_manifest_design_system_field.py` asserting `ReproducibilityManifest.design_system_version` exists, is required, and validates against `^\d+\.\d+\.\d+(?:[-+].+)?$`
- [x] T022 [Foundational] Extend `packages/shared-types/src/shared_types/report.py` adding `design_system_version: str` to `ReproducibilityManifest` (turns T021 green); update existing tests that construct manifests
- [x] T023 [P] [Foundational] Update existing feature 001 manifest-creation sites in `packages/analysis-core/src/analysis_core/manifest.py` to pull `design_system.version.__version__` and pass it into the manifest builder

### Cross-feature: extend forbidden-terms fixtures

- [x] T024 [P] [Foundational] Seed `tests/fixtures/forbidden-terms/en.txt` with the v1.0.0 list (≥12 entries: "cheater", "cheating", "cheat detected", "guilty", "fraud", "fraudster", "criminal", "confirmed cheating", "verdict", "convicted", "accused", "perpetrator") with header comment declaring `# version: 1.0.0` and three-column TSV body
- [x] T025 [P] [Foundational] Seed `tests/fixtures/forbidden-terms/pt.txt` with the parallel Portuguese v1.0.0 list (≥12 entries: "trapaceiro", "trapaça", "culpado", "fraudador", "fraude", "criminoso", "trapaça confirmada", "veredicto", "condenado", "acusado", "perpetrador", "violação") matching schema of T024

**Checkpoint**: all foundational tests pass; `uv run mypy` + `uv run ruff check` clean across the new package and the feature 001 edits.

---

## Phase 3: User Story 1 — Brand-compliant report bundle export (Priority: P1) 🎯 MVP

**Goal**: every PDF/HTML produced by feature 001 `cleanmatch export` is locked to the forensic-analytics palette + typography + lexicon, with `design_system_version` in the manifest.

**Independent Test**: rendering the 50-game canonical report passes all four audits (palette, typography, motion-static, lexical) on first run; rendering twice yields byte-identical PDFs (cross-checks feature 001 SC-004); no pixel of any rendered page falls in the forbidden-hue range.

### tokens.json + WeasyPrint adapter

- [x] T026 [P] [US1] Write failing golden-file test in `packages/design-system/tests/golden/test_compile_weasyprint.py` asserting that compiling the v1.0.0 `tokens.json` produces a byte-identical `adapters/weasyprint/tokens.css`
- [x] T027 [P] [US1] Write failing unit test verifying the generated CSS uses only WeasyPrint subset features (no `grid`, no `:has()`, no container queries; parsed via `tinycss2`) in `packages/design-system/tests/unit/test_weasyprint_subset.py`
- [x] T028 [US1] Author `packages/design-system/src/design_system/tokens/tokens.json` per `contracts/token-file-schema.md` (full v1.0.0 token set: palette + extended chart series + typography + spacing + radius + shadow + motion + z_index)
- [x] T029 [US1] Implement `packages/design-system/src/design_system/tokens/compile_weasyprint.py` (turns T026-T027 green); commit the generated `packages/design-system/adapters/weasyprint/tokens.css`
- [x] T030 [P] [US1] Add Inter + Manrope OFL font subsets at `packages/design-system/adapters/weasyprint/fonts/{Inter-{400,500,600,700}.woff2,Manrope-{400,500,600,700}.woff2}` (Latin + Latin Extended-A only) with `LICENSE.OFL` next to them

### Palette audit (Track A + Track B)

- [x] T031 [P] [US1] Write failing unit tests for Track A (CSS lint) covering: unknown literal `#xxxxxx`, forbidden hue inside an `rgba(...)`, allowed token references in `packages/design-system/tests/unit/test_audit_palette_css.py`
- [x] T032 [P] [US1] Write failing unit tests for Track B (pixel) covering: synthetic PNG with all-palette pixels passes, synthetic PNG with one red pixel fails on `forbidden_hue`, fringe-tolerance counting in `packages/design-system/tests/unit/test_audit_palette_pixel.py`
- [x] T033 [US1] Implement Track A in `packages/design-system/src/design_system/audits/palette.py::audit_generated_css` (turns T031 green)
- [x] T034 [US1] Implement Track B in `packages/design-system/src/design_system/audits/palette.py::audit_pdf` and `::audit_image` using `colormath` Delta-E + HSL forbidden-hue check (turns T032 green); depends on T033

### Typography audit

- [x] T035 [P] [US1] Write failing unit tests for `audit_html` (selectolax-based): metric element with correct tokens passes, with wrong font-weight fails on `wrong_metric_typography` in `packages/design-system/tests/unit/test_audit_typography_html.py`
- [x] T036 [P] [US1] Write failing unit tests for `audit_pdf` (pdfminer-based) parallel to T035 in `packages/design-system/tests/unit/test_audit_typography_pdf.py`
- [x] T037 [US1] Implement `packages/design-system/src/design_system/audits/typography.py` covering HTML and PDF modes (turns T035-T036 green)

### Motion audit (static CSS only in MVP)

- [x] T038 [P] [US1] Write failing unit tests in `packages/design-system/tests/unit/test_audit_motion_static.py` covering: CSS with token-derived `transition` passes, CSS with literal `linear` easing fails, CSS with duration `500ms` fails
- [x] T039 [US1] Implement `packages/design-system/src/design_system/audits/motion.py::audit_static_css` (turns T038 green); the dynamic Playwright audit is a placeholder that returns `skipped` in MVP

### Lexical audit

- [x] T040 [P] [US1] Write failing unit tests for `audit_text` covering: word_boundary vs substring modes, case-insensitivity, multi-language scan in `packages/design-system/tests/unit/test_audit_lexical.py`
- [x] T041 [P] [US1] Write failing integration tests for `audit_pdf`, `audit_html`, `audit_template`, `audit_json` covering PDF text extraction edges and template scanning in `packages/design-system/tests/unit/test_audit_lexical_io.py`
- [x] T042 [US1] Implement `packages/design-system/src/design_system/audits/lexical.py` (turns T040-T041 green)

### CLI + manifest field producer

- [x] T043 [US1] Add the `python -m design_system.audits.palette|typography|motion|lexical` CLI entry-points in `packages/design-system/src/design_system/__main__.py` matching the contracts' exit-code tables
- [x] T044 [US1] Add the `python -m design_system audit-replay <run-id>` CLI in `packages/design-system/src/design_system/__main__.py` per `contracts/manifest-field.md`

### Wire feature 001 report-engine to the design system

- [ ] T045 [P] [US1] Write failing integration test `packages/report-engine/tests/test_palette_compliance.py` asserting the canonical 50-game fixture report passes the palette audit (both tracks)
- [ ] T046 [P] [US1] Write failing integration test `packages/report-engine/tests/test_typography_compliance.py` asserting the same fixture passes the typography audit on PDF + HTML
- [ ] T047 [P] [US1] Write failing integration test `packages/report-engine/tests/test_motion_static_compliance.py` asserting the static CSS passes the motion audit
- [ ] T048 [P] [US1] Write failing integration test `packages/report-engine/tests/test_lexical_compliance.py` asserting the rendered PDF, HTML, JSON, and Jinja2 templates all pass the lexical audit (en + pt)
- [ ] T049 [P] [US1] Write failing integration test `packages/report-engine/tests/test_manifest_design_system_version.py` asserting every rendered manifest contains a non-empty `design_system_version` matching the running package version (SC-008)
- [ ] T050 [US1] Implement `packages/report-engine/src/report_engine/styles.py` exposing `get_weasyprint_css_path()` and `get_design_system_version()` that delegate to `design_system`
- [ ] T051 [US1] Update `packages/report-engine/src/report_engine/templates/base.html` to `@import url("…/design-system/adapters/weasyprint/tokens.css")` and adopt the locked Jinja macros for Analytical Card, Risk Pill, Timeline, Heuristic Badge, Manifest Block, Code Inline
- [ ] T052 [US1] Update `packages/report-engine/src/report_engine/render_pdf.py` to use the bundled OFL fonts via WeasyPrint `@font-face` declarations from the design-system adapter
- [ ] T053 [US1] Update `packages/report-engine/src/report_engine/render_pdf.py` and `render_html.py` to embed `design_system.version.__version__` in the manifest output (turns T049 green)
- [ ] T054 [US1] Adopt the analytical lexicon in `packages/report-engine/src/report_engine/narrative.py`: every narrative caption uses canonical terms from `entries_en.json` / `entries_pt.json` (turns T048 green for narrative paths)
- [ ] T055 [US1] Replace any colour literals in `packages/report-engine/src/report_engine/charts.py` (matplotlib SVG charts) with the design-system chart-series palette so charts pass Track B of the palette audit (turns T045 green for chart pixels)
- [ ] T056 [US1] Add risk-pill rendering in `packages/report-engine/src/report_engine/render_html.py` using the locked `RiskTreatment` constants (LOW gray, MEDIUM amber, HIGH signal-yellow) — never red
- [ ] T057 [US1] Run all four audits against the canonical fixture report end-to-end via `uv run pytest -m "audit_palette or audit_typography or audit_motion or audit_lexical"`; confirm zero findings and that the byte-stability test from feature 001 T080 still passes (no regression in determinism)
- [ ] T058 [US1] Run coverage on `packages/design-system/src/` and `packages/report-engine/src/` and confirm ≥85% line / ≥80% branch

**Checkpoint**: User Story 1 is fully functional. Every PDF/HTML rendered by feature 001 now passes the four-audit gate and the manifest stamps the design-system version.

---

## Phase 4: User Story 2 — Forensic web UI parity (Priority: P2)

**Goal**: scaffold Phase 3 web adapters and the dynamic motion audit so the brand definition is unblocked the moment `apps/frontend` is built. Phase 4 ships only the *scaffolding + compile pipeline + dynamic-audit harness*; full web pages remain Phase 3.

**Independent Test**: `compile_tailwind.py` and `compile_css_vars.py` produce byte-stable artefacts under `adapters/{tailwind,css-vars}/` matching golden fixtures; the dynamic motion audit (Playwright harness) green-runs against a one-page synthetic web fixture that uses the generated theme.

### Tailwind adapter

- [ ] T059 [P] [US2] Write failing golden-file test in `packages/design-system/tests/golden/test_compile_tailwind.py` asserting that compiling v1.0.0 `tokens.json` produces a byte-identical `adapters/tailwind/theme.ts`
- [ ] T060 [P] [US2] Implement `packages/design-system/src/design_system/tokens/compile_tailwind.py` emitting a TypeScript theme object compatible with Tailwind v4 (`@theme` block / `theme.ts` export) (turns T059 green); commit the generated artefact

### CSS-variables adapter

- [ ] T061 [P] [US2] Write failing golden-file test for `compile_css_vars.py` in `packages/design-system/tests/golden/test_compile_css_vars.py`
- [ ] T062 [P] [US2] Implement `packages/design-system/src/design_system/tokens/compile_css_vars.py` emitting `:root { --color-background: #0B0B0D; ... }` (turns T061 green); commit `adapters/css-vars/tokens.css`

### shadcn theme placeholder

- [ ] T063 [P] [US2] Add `packages/design-system/adapters/shadcn/components.json` skeleton + a `README.md` explaining the Phase 3 integration steps and the locked `RiskTreatment` recipe for shadcn's variant API

### Framer Motion adapter

- [ ] T064 [P] [US2] Write failing golden-file test for `compile_framer_motion.py` producing a TS variants object that exports the single easing curve + duration tokens
- [ ] T065 [P] [US2] Implement `packages/design-system/src/design_system/tokens/compile_framer_motion.py` and commit `adapters/framer-motion/variants.ts` (turns T064 green)

### Dynamic motion audit (Playwright harness)

- [ ] T066 [P] [US2] Write failing harness test in `packages/design-system/tests/unit/test_audit_motion_dynamic.py` that exercises a synthetic page (under `tests/fixtures/web/synthetic.html`) and asserts the captured transitions are within `[200, 350]` ms and the easing matches the locked curve
- [ ] T067 [US2] Implement the Playwright-backed `audit_web` in `packages/design-system/src/design_system/audits/motion.py` plus the interaction inventory in `motion_interactions.py` (turns T066 green); skip-marked unless `CLEANMATCH_WEB_AUDIT=1` is set
- [ ] T068 [P] [US2] Add `tests/fixtures/web/synthetic.html` + `tests/fixtures/web/synthetic.css` consuming the generated Tailwind theme + Framer Motion variants for the harness above
- [ ] T069 [US2] Confirm `motion_overrides.json` exists at `packages/design-system/src/design_system/audits/motion_overrides.json` with `{ "overrides": [] }` initially, and that an integration test in `tests/unit/test_motion_overrides.py` asserts the parser, the expiry check, and the "expired override fails the audit" rule

**Checkpoint**: All Phase-3-bound adapters compile deterministically and the dynamic motion audit harness is green on the synthetic fixture. Real web pages remain Phase 3.

---

## Phase 5: User Story 3 — Contributor authoring without guessing (Priority: P3)

**Goal**: a new contributor can build a new surface (PDF section, web panel, narrative caption) using only the published artefacts and pass all four audits on first commit.

**Independent Test**: SC-007 — across ≥3 onboarding events, a contributor given the docs + a brief ships a passing first-commit surface.

### Documentation

- [ ] T070 [P] [US3] Write `packages/design-system/docs/CONTRIBUTING.md` covering: how to add a token (MINOR bump), how to add a component (MINOR), how to extend the lexicon, how to add a forbidden term, how to override motion legitimately
- [ ] T071 [P] [US3] Write `packages/design-system/docs/COMPONENTS.md` documenting every component in `catalogue.json` with: tokens-of-record table, states, accessibility requirements, surfaces supported, example markup
- [ ] T072 [P] [US3] Write `packages/design-system/docs/LEXICON.md` rendering the en/pt lexicon as a side-by-side reference table with definitions, preferred alternatives, and forbidden alternatives
- [ ] T073 [P] [US3] Write `packages/design-system/docs/AUDITS.md` with one section per audit including: scope, how to run, common failure modes, override procedure (where applicable)
- [ ] T074 [P] [US3] Update `specs/002-design-system/quickstart.md` references in root `README.md` so the discovery path from the repo root is one click

### Component catalogue completion

- [ ] T075 [P] [US3] Write failing unit tests for each catalogue entry (analytical-card, risk-pill, timeline, heuristic-badge, manifest-block, code-inline) covering tokens-of-record resolution + state list completeness in `packages/design-system/tests/unit/test_catalogue_entries.py`
- [ ] T076 [US3] Author `packages/design-system/src/design_system/components/catalogue.json` with the v1.0.0 component set (turns T075 green); accessibility requirements per data-model §5

### Lexicon v1.0.0 entries

- [ ] T077 [P] [US3] Seed `packages/design-system/src/design_system/lexicon/entries_en.json` with the v1.0.0 set: Behavioral Signal, Statistical Irregularity, Complexity Correlation, Tactical Precision Burst, Risk Window, Analytical Confidence + 5 more sourced from spec FR-011
- [ ] T078 [P] [US3] Seed `packages/design-system/src/design_system/lexicon/entries_pt.json` parallel to T077 with Portuguese definitions

### Audit replay CLI end-to-end

- [ ] T079 [US3] Write failing integration test in `packages/design-system/tests/unit/test_audit_replay.py` covering: replay against a fixture manifest with the current version (passes), replay with an embedded older version (warns) per `contracts/manifest-field.md`
- [ ] T080 [US3] Implement the replay flow in `packages/design-system/src/design_system/__main__.py::audit_replay` (turns T079 green); depends on T044

**Checkpoint**: A contributor reading only the docs can author a new surface that passes all audits.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T081 [P] Add audit-performance benchmarks in `packages/design-system/benchmarks/bench_audits.py`: palette Track A ≤ 100 ms, Track B ≤ 5 s on a 50-game PDF, typography PDF ≤ 2 s, lexical (both languages) ≤ 1 s, motion static ≤ 100 ms
- [ ] T082 [P] Wire `bench_audits.py` into CI as a labelled job that fails on >10% regression (matches constitution Principle IV enforcement model from feature 001)
- [ ] T083 [P] Add the v1.0.0 release entry in `packages/design-system/CHANGELOG.md` listing every token, component, lexicon entry, and forbidden term shipped
- [ ] T084 [P] Add a design-system-aware PR template at `.github/pull_request_template.md` (replacing the feature 001 stub if present) that requires: "audits ran clean", "design-system version bump categorisation (MAJOR/MINOR/PATCH)", and "forbidden-terms file diff intentional?"
- [ ] T085 [P] Add WCAG contrast-pair table at `packages/design-system/src/design_system/audits/wcag_pairs.json` and a test in `tests/unit/test_wcag_pairs.py` asserting every locked pair clears its minimum (SC-005)
- [ ] T086 [P] Add the colour-blindness regression check in `packages/design-system/tests/unit/test_colour_blindness.py` simulating deuteranopia on the 6-series chart palette and asserting min pairwise Delta-E ≥ 10
- [ ] T087 [P] Add the "monochrome / colour-blind risk indicator fallback" — every `RiskTreatment` carries a glyph (○ / ◐ / ●) in addition to the colour treatment; component tests assert the glyph is present in catalogue entries (CHK037)
- [ ] T088 [P] Run the full audit + benchmark suite, capture the coverage report, and update root `README.md` with the v1.0.0 design-system badge + a one-line description ("Forensic Analytics Design System v1.0.0 — audits enforced in CI")
- [ ] T089 [P] Run the design-system audits against every existing report fixture in `tests/fixtures/pgn/known-clean/` and `tests/fixtures/pgn/known-suspect/` produced by feature 001 to confirm no historical artefact regresses
- [ ] T090 Tag the v1.0.0 release: bump `packages/design-system/pyproject.toml`, update `version.py`'s `__version__`, regenerate every committed adapter artefact, commit the diff, and verify feature 001's manifest now stamps `design_system_version = "1.0.0"`

---

## Phase 7: Remediation (from /speckit-analyze HIGH findings)

These tasks were added after the initial /speckit-analyze pass surfaced
five HIGH findings; they tighten existing contracts rather than expand
scope. They MUST land before `/speckit-implement` starts on US1.

### A1 — token tie-in for HIGH risk treatment

(No new task — fully resolved by spec.md FR-007 and data-model.md §8
edits. T017 implementation MUST reference `color.signal` for the HIGH
foreground binding.)

### A2 — `Headline-Metric` / `metric-card-headline` role markers

- [ ] T091 [P] [US1] Write failing typography-audit unit test in `packages/design-system/tests/unit/test_audit_typography_role.py` covering: untagged metric numeral fails with `missing_metric_role`; tagged-but-wrong-typography fails with `wrong_metric_typography`; tagged-and-correct passes
- [ ] T092 [US1] Extend `packages/design-system/src/design_system/audits/typography.py` to emit `missing_metric_role` findings whenever a node uses `typography.metric` without the role marker (turns T091 green); update feature 001 templates (`packages/report-engine/src/report_engine/templates/base.html` and PDF structure-tree producer in `render_pdf.py`) to tag every headline metric with `data-role="metric-card-headline"` (HTML) or PDF structure role `Headline-Metric`

### C2 / I1 — risk-indicator Track-C audit + producer tagging

- [ ] T093 [P] [US1] Write failing unit test in `packages/design-system/tests/unit/test_audit_palette_risk.py` covering: untagged risk indicator fails with `missing_risk_role`; tagged-but-off-recipe fails with `risk_treatment_non_canonical`; tagged-and-canonical passes for each of LOW / MEDIUM / HIGH
- [ ] T094 [US1] Implement Track C in `packages/design-system/src/design_system/audits/palette.py::audit_risk_indicators` per `contracts/audit-palette.md` Track-C section (turns T093 green); extend the risk-pill rendering introduced by T056 in `packages/report-engine/src/report_engine/render_html.py` and the PDF structure-tree producer in `packages/report-engine/src/report_engine/render_pdf.py` to emit the role marker (`data-role="risk-pill"` / PDF role `Risk-Pill`) and to consume `RiskTreatment` constants exclusively
- [ ] T095 [P] [US1] Wire Track C invocation into the existing palette compliance test in `packages/report-engine/tests/test_palette_compliance.py` (T045) so every rendered fixture exercises the risk-indicator check

### C1 — SC-006 usability protocol

- [ ] T096 [P] Author `packages/design-system/docs/SC006_USABILITY.md` defining: panel-selection rule (n≥5 non-technical readers, no chess.com fairplay-policy familiarity), interview script, pass/fail tally template, "analytical/forensic" / "anti-cheat/accusatory" word-bank for unprompted-response coding, and where to record results (`packages/design-system/docs/SC006_RESULTS.md`); the doc itself MUST pass the lexical audit (en + pt where applicable)

### C3 — SC-007 onboarding measurement infrastructure

- [ ] T097 [P] Author `packages/design-system/docs/SC007_ONBOARDING_LOG.md` defining: "onboarding event" (a PR labelled `onboarding-event` whose author has fewer than 3 prior commits to `packages/design-system/` or `packages/report-engine/`), pass criterion (all four audits clean on first commit, before any maintainer push), tally template (`SC007_RESULTS.md` with rows of date, contributor, PR URL, pass/fail); add a CI step in `.github/workflows/ci.yml` that, on labelled PRs, appends a row to `SC007_RESULTS.md` and re-evaluates the rolling ≥3-event passing-rate; the doc itself MUST pass the lexical audit

### C4 — PDF reduced-motion explicit invariant

- [ ] T098 [P] [US1] Write unit test `packages/design-system/tests/unit/test_pdf_reduced_motion.py` asserting the generated `adapters/weasyprint/tokens.css` contains zero `transition` and zero `animation` CSS declarations; enforces FR-014 trivially for the PDF surface (which has no motion) and prevents future drift from accidentally adding animated CSS to the PDF adapter

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)** — no dependencies; start immediately.
- **Phase 2 (Foundational)** — depends on Phase 1. T022/T023 touch feature 001 packages and MUST land before any consumer test depending on the new manifest field.
- **Phase 3 (US1)** — depends on Phase 2. MVP target.
- **Phase 4 (US2)** — depends on Phase 2 + the audit primitives from US1 (T033-T042). Scaffolding only; real web pages stay Phase 3.
- **Phase 5 (US3)** — depends on Phase 2 + US1 audits + US2 adapters being green. Lexicon files (T077-T078) are independent of T076 ordering and may parallelise.
- **Phase 6 (Polish)** — depends on the user stories shipping clean.
- **Phase 7 (Remediation)** — added after /speckit-analyze HIGH findings; T091-T095 belong logically to US1 and MUST land before Phase 6 / v1.0.0 tag. T096 belongs logically to Polish but is grouped under Phase 7 for traceability to the analysis pass.

### User Story dependencies

- US1 has no dependency on US2/US3.
- US2 reuses US1's audit primitives; scaffolds Phase 3 surfaces; can parallelise with US3 doc work.
- US3 reuses US1 + US2 artefacts; the audit-replay CLI requires the manifest field landed by T022.

### Within each user story

- Red-first: every test task precedes its implementation task (constitution Principle II).
- Token loader (T010) precedes adapter compiles (T028-T029, T060, T062, T065).
- `risk_treatments.py` (T017) precedes any report-engine risk-pill rendering (T056).
- Cross-feature edits (T022, T023, T054) MUST be sequenced before integration tests in `packages/report-engine/tests/` (T049 onwards).

### Parallel opportunities

- All Phase 1 setup tasks `[P]` run in parallel.
- Phase 2 schema test tasks (T008, T012, T013, T015, T018) all parallel before their implementations.
- Phase 3 audit unit tests (T031-T032, T035-T036, T038, T040-T041) all parallel.
- Phase 3 integration tests against feature 001 (T045-T049) all parallel.
- Phase 4 adapter compiles (T059-T065) all parallel after T010.
- Phase 5 doc tasks (T070-T074) all parallel.

---

## Parallel Example: Phase 3 (US1) red-first audit tests

```bash
# Author the failing test files for all four audits at once:
Task: "Write failing palette CSS lint tests in packages/design-system/tests/unit/test_audit_palette_css.py"     # T031
Task: "Write failing palette pixel tests in packages/design-system/tests/unit/test_audit_palette_pixel.py"      # T032
Task: "Write failing typography HTML tests in packages/design-system/tests/unit/test_audit_typography_html.py"  # T035
Task: "Write failing typography PDF tests in packages/design-system/tests/unit/test_audit_typography_pdf.py"    # T036
Task: "Write failing motion static tests in packages/design-system/tests/unit/test_audit_motion_static.py"      # T038
Task: "Write failing lexical scanner tests in packages/design-system/tests/unit/test_audit_lexical.py"          # T040
Task: "Write failing lexical IO tests in packages/design-system/tests/unit/test_audit_lexical_io.py"            # T041
Task: "Write failing report-engine palette compliance test in packages/report-engine/tests/test_palette_compliance.py" # T045
Task: "Write failing report-engine typography compliance test in packages/report-engine/tests/test_typography_compliance.py" # T046
Task: "Write failing report-engine motion compliance test in packages/report-engine/tests/test_motion_static_compliance.py" # T047
Task: "Write failing report-engine lexical compliance test in packages/report-engine/tests/test_lexical_compliance.py" # T048
Task: "Write failing manifest version test in packages/report-engine/tests/test_manifest_design_system_version.py" # T049
```

---

## Implementation Strategy

### MVP first (User Story 1 only)

1. Phase 1: Setup.
2. Phase 2: Foundational (BLOCKS everything else, including the cross-feature manifest extension).
3. Phase 3: User Story 1 — every report passes the four audits.
4. **STOP and VALIDATE**: run the full canonical fixture suite end-to-end; confirm all four audits clean + manifest stamped + byte-stability preserved.
5. Tag a `design-system 0.1.0` pre-release; feature 001 reports now carry the brand.

### Incremental delivery

1. Setup + Foundational + US1 → reports are brand-locked. Pre-release tag.
2. Add US2 scaffolding → Tailwind/CSS-vars/Framer Motion adapters byte-stable; dynamic motion audit harness green.
3. Add US3 documentation + lexicon completion + audit-replay → contributor onboarding ready.
4. Polish + benchmark gate + v1.0.0 tag.

### Parallel team strategy

After Phase 2 completes:

- Workstream A (US1, primary): authoring `tokens.json`, the WeasyPrint adapter, the four audits, and wiring feature 001's report-engine.
- Workstream B (US2): adapter compile pipeline (Tailwind, CSS-vars, Framer Motion) + dynamic motion audit harness. Can run in parallel with A; depends only on the token loader.
- Workstream C (US3): documentation + lexicon entries + replay CLI. Depends on T020 + T022 only.

---

## Notes

- `[P]` tasks touch disjoint files.
- `[Story]` tag maps each task to its user story for traceability.
- Tests precede implementation (constitution Principle II is NON-NEGOTIABLE).
- Coverage gate 85/80 enforced in CI on `packages/design-system/src/`.
- Adapter compile artefacts are *committed* (not generated at install time) so reviewers see drift and consumers don't run the compiler.
- Cross-feature contract with `001-fairplay-analysis`: `ReproducibilityManifest.design_system_version` is the only schema change; the forbidden-terms TSV format stays as feature 001 declared.
- "No red, anywhere" is structural: enforced by the loader (T010), the palette audit (T034), and the chart-series palette (T028 / T055).
- Commit after each task or logical group; never amend a commit that already passed CI.
- Stop at any checkpoint to validate user-story independence.
- Avoid: vague tasks, same-file conflicts within a phase, cross-story dependencies that break MVP independence.
