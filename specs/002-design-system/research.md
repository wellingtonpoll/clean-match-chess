# Phase 0 Research — Forensic Analytics Design System

**Feature**: `002-design-system` · **Date**: 2026-05-23

Stack and design decisions taken before Phase 1 contract work. Each entry
lists what was chosen, why, and the alternatives rejected. No
`NEEDS CLARIFICATION` markers remain.

---

## 1. Token file format

- **Decision**: W3C Design Tokens Community Group (DTCG) JSON, single
  file `packages/design-system/src/design_system/tokens/tokens.json`.
  Every token carries `$value`, `$type`, and `$description`. Composite
  tokens (typography, shadow, motion) follow the DTCG composite spec.
- **Rationale**: DTCG is the closest thing to an industry standard, has
  tooling support (Style Dictionary, Token Studio), and lets adapters be
  pure compile steps. Single file keeps git diffs reviewable and the
  manifest hash trivial.
- **Alternatives**:
  - YAML — more human-friendly but ambiguous on numeric types and
    leading zeros; rejected.
  - Style Dictionary's bespoke JSON — popular but vendor-specific;
    rejected in favour of the open DTCG spec.
  - One file per category — easier to read but harder to atomic-hash;
    rejected.

## 2. Compilation strategy (single SoT → many surfaces)

- **Decision**: Pure compile from `tokens.json` to each adapter via small
  Python functions in `packages/design-system/src/design_system/tokens/
  compile_*.py`. The MVP ships `compile_weasyprint.py`; Phase 3 will add
  `compile_tailwind.py` and `compile_css_vars.py`. Generated artefacts
  live under `packages/design-system/adapters/<target>/` and are
  committed (so reviewers see the diff and consumers don't need to run
  the compiler at install time).
- **Rationale**: Committed generated artefacts give us byte-stable
  consumer surfaces (PDF render is deterministic), turn compile
  regressions into ordinary PR diffs, and avoid build-step coupling for
  consumers. The compile functions are unit-testable with golden files.
- **Alternatives**:
  - Style Dictionary CLI — Node toolchain dragged into a Python-first
    repo; rejected for MVP, reconsider in Phase 3 if Tailwind needs it.
  - Runtime compile on each report render — slower, non-deterministic
    risk; rejected.

## 3. WeasyPrint CSS subset

- **Decision**: The WeasyPrint adapter restricts generated CSS to the
  intersection of WeasyPrint 60+'s documented subset and Print Page
  Module Level 3. No CSS Grid, no `:has()`, no container queries, no
  `inset-block-*`, no logical properties beyond `margin-*`. Layout uses
  flexbox and tables. Variables (`--*`) ARE supported and used heavily.
- **Rationale**: WeasyPrint is the PDF renderer in feature 001; the
  design system can only earn its "single source of truth" claim if
  every token compiles to PDF without manual fallback. The subset is
  documented and stable as of WeasyPrint 60.
- **Alternatives**:
  - Playwright PDF — supports full CSS but heavyweight; deferred to
    Phase 3 along with frontend tooling.
  - Two separate themes (one for PDF, one for web) — exact thing the
    design system exists to prevent; rejected.

## 4. Palette audit method

- **Decision**: Two-track audit.
  - **Track A — generated artefact lint**: parse the generated
    WeasyPrint CSS and verify every colour value resolves to a locked
    token; reject any literal `#xxxxxx` that is not in the palette.
  - **Track B — rendered pixel audit**: rasterise each page of the
    rendered PDF (or screenshot the rendered HTML/web view) at 144 DPI,
    convert to Lab colour space, and assert every pixel is within
    Delta-E ≤ 5.0 of a locked palette colour. Allow ≤ 1% per-page
    anti-aliasing fringe (matches SC-001 tolerance).
  - **Forbidden-hue check** runs over the same pixel pass: any pixel
    with HSL hue in `[350°, 360°] ∪ [0°, 20°]` and HSL saturation > 30 %
    (0–100 % range) fails.
- **Rationale**: Track A is cheap and catches authoring drift; Track B
  catches anti-aliasing, chart libraries, font hinting, and image
  embedding. Together they make "no red, anywhere" structural.
- **Alternatives**:
  - Pixel-only — misses authoring drift before render.
  - CSS-only — misses chart libraries and embedded images.
  - DOM-only audit (no render) — misses what the user actually sees.

## 5. Risk treatment recipe

- **Decision**: Three locked recipes, all dark-background:
  - `LOW`: `bg = surface (#171717)`, `fg = muted (#A1A1AA)`,
    `border = border (#2A2A2E)`.
  - `MEDIUM`: `bg = surface`, `fg = amber (#F4B41F)` (yellow-shifted,
    distinct from Signal Yellow `#F4D21F`), `border = amber`.
  - `HIGH`: `bg = background (#0B0B0D)`, `fg = signal (#F4D21F)`,
    `border = signal`, with the metrics number weight forced to 700.
- **Rationale**: Amber `#F4B41F` is darker yellow that reads as
  "elevated" without crossing into orange/red. The audit's
  forbidden-hue check passes on amber (hue ≈ 47°).
- **Alternatives**:
  - Single yellow for both MEDIUM and HIGH — collapses the categorical
    signal; rejected.
  - Saturated orange for MEDIUM — close to red; rejected.

## 6. Chart-series extended palette

- **Decision**: A 6-colour ordered series palette derived from Signal
  Yellow + Neutral Gray family:
  1. `#F4D21F` (Signal Yellow)
  2. `#F4B41F` (Amber)
  3. `#A1A1AA` (Neutral Gray)
  4. `#6B6B73`
  5. `#3E3E45`
  6. `#F5F5F2` (Soft White; for inverted bg cases)
- **Rationale**: Avoids red. Distinguishable both for normal vision
  (luminance ladder) and for deuteranopia (verified via Coblis
  simulation; minimum pairwise Delta-E in deuteranopia simulation
  ≥ 10).
- **Alternatives**:
  - Tableau 10 / Category 10 — includes red; rejected.
  - Viridis-style perceptually uniform — too colourful for the
    forensic positioning; rejected.

## 7. Lexicon + forbidden-terms schema

- **Decision**: Two artefact families:
  - `entries_<lang>.json` — canonical analytical lexicon. One JSON file
    per language with array of objects:
    `{ "term", "definition", "context", "alternatives_preferred", "alternatives_forbidden" }`.
  - `tests/fixtures/forbidden-terms/<lang>.txt` — TSV owned by feature
    001 with rows `term\tcategory\tmatch_mode`. The design system
    *extends* this file (FR-012 of this feature; SC-008 of feature 001
    cites the same file).
- **Rationale**: Two files because they have different consumers: the
  rich lexicon is for documentation and code completion; the TSV is for
  the runtime lexical audit (cheap, line-oriented).
- **Alternatives**:
  - One combined YAML — split is intentional; lexical audit must be
    O(n) over rendered text with a simple scanner.

## 8. Lexical audit method

- **Decision**: Per-language scanner using compiled regex per
  forbidden-term entry; `word_boundary` mode uses `\bTERM\b`,
  `substring` mode uses literal substring with case-insensitive match.
  PDF text extracted via `pdfminer.six`; HTML text via `selectolax`;
  CLI human output via simple stdout/stderr capture. JSON output is
  flattened to its string values before scanning.
- **Rationale**: Plain regex is fast (≤ 1 s budget for both languages on
  a 50-game PDF) and easy to audit. `pdfminer.six` produces stable text
  output for fixture diffs. `selectolax` parses HTML faster than
  BeautifulSoup with a smaller dependency footprint.
- **Alternatives**:
  - spaCy / NLP-based — overkill; rejected.
  - Tesseract OCR of rendered images — slow and adds an OS dep;
    rejected. (The pixel-palette audit doesn't need text — it operates
    on hue/value.)

## 9. Typography & font licensing

- **Decision**: Inter (open-source SIL Open Font License) bundled into
  the repository under `packages/design-system/adapters/weasyprint/
  fonts/` for PDF embedding. Manrope (SIL OFL) bundled as fallback for
  contexts where Inter cannot be licensed. Subset to Latin + Latin
  Extended-A to keep the PDF small.
- **Rationale**: Both fonts are OFL → embedded in PDF without
  restriction. Subset keeps PDFs ≤ 200 KB for a typical 1-game report.
- **Alternatives**:
  - System fonts only — PDF rendering varies across machines, breaks
    determinism (feature 001 FR-017).
  - Web fonts at runtime — non-deterministic; rejected.

## 10. Motion grammar implementation

- **Decision**: Single token `motion.easing.standard =
  cubic-bezier(0.22, 1, 0.36, 1)` and a duration range
  `[200ms, 350ms]`. Phase 3 Framer Motion variants compile from this
  single source. The motion audit (web only) instruments
  `requestAnimationFrame` to measure transition durations and asserts
  every measured transition stays within the bounded range. The MVP PDF
  pipeline has no motion, so the motion audit is a no-op on PDF.
  `prefers-reduced-motion` collapses all transitions to 0 ms.
- **Rationale**: Single curve is the easiest enforcement story. If a
  legitimate need for a different curve arises, FR-005 of the spec
  already requires "explicit, documented override" — handled by a
  reviewer-approved exception list.
- **Alternatives**:
  - Tiered curve catalogue — premature; revisit if motion needs
    diversify in Phase 3.

## 11. Versioning + manifest field

- **Decision**: `packages/design-system/pyproject.toml` carries the
  semver. `design_system.version.__version__` is the single source. The
  feature 001 `ReproducibilityManifest` gets a new field
  `design_system_version` (string) populated at render time. Feature
  001's manifest schema is extended in lockstep.
- **Rationale**: Single source for versioning, one field to add to the
  manifest, fits the cross-feature contract (CHK023, CHK046 of `ux.md`).
- **Alternatives**:
  - Per-adapter versions — adds drift surface; rejected.

## 12. Accessibility audits

- **Decision**: A WCAG contrast check runs as part of the palette audit
  using `colormath`'s WCAG-formula contrast ratio. The locked token
  pairs (`text on background`, `signal on background`, `signal on
  surface`, `muted on background`, etc.) are listed in
  `packages/design-system/src/design_system/audits/wcag_pairs.json`.
  Each pair has a required minimum (≥4.5:1 small text, ≥3:1 large text
  / non-text). Pair failures are CI-blocking.
- **Rationale**: Hard-coding the contrast pairs and minimums turns
  SC-005 into a CI green/red rather than a manual review item.

## 13. CI integration

- **Decision**: Four audit modules expose a unified `pytest` plugin
  (`packages/design-system/src/design_system/audits/pytest_plugin.py`)
  registering marks: `@pytest.mark.audit_palette`,
  `@pytest.mark.audit_typography`, `@pytest.mark.audit_motion`,
  `@pytest.mark.audit_lexical`. Feature 001's report-engine tests use
  these marks to attach the audits to every rendered fixture.
  `.github/workflows/ci.yml` runs `uv run pytest -m audit_*` after the
  base test suite; any failure blocks merge (FR-017 of this feature).
- **Rationale**: pytest is already the test runner; a plugin keeps
  consumer wiring minimal.
- **Alternatives**:
  - Standalone audit CLI invoked separately — duplicates pytest's
    fixture/plugin machinery.

## 14. Cross-cutting deferred decisions

- **Light-mode tokens**: deferred (Assumptions). Will land as a new
  theme block in `tokens.json` when introduced.
- **shadcn/ui theming + Tailwind v4**: scaffolded as empty placeholders
  under `adapters/{tailwind,shadcn}/`; populated in Phase 3.
- **Framer Motion variants**: scaffolded under `adapters/framer-motion/`;
  populated in Phase 3.
- **Storybook / component playground**: out of scope for MVP; the
  consumer surface is the PDF + HTML report only.
- **External CDN font hosting**: out of scope; fonts are bundled.

---

**Outcome**: All Technical Context items are resolved. Phase 1 can proceed.
