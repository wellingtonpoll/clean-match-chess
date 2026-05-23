# Feature Specification: Forensic Analytics Design System

**Feature Branch**: `002-design-system`

**Created**: 2026-05-23

**Status**: Draft

**Input**: User description: "Style guide extraído da imagem — paleta Obsidian Black / Soft White / Signal Yellow, tipografia Inter ou Manrope, cartões analíticos com border-radius 20–28 px, timeline visualization, sistema de risco LOW/MEDIUM/HIGH (sem vermelho), motion lento e preciso, vocabulário analítico (Behavioral Signal, Statistical Irregularity…) e nunca acusatório, stack alvo Next.js + Tailwind + shadcn/ui + ECharts + Framer Motion + Lucide, posicionamento como forensic analytics platform e não anti-cheat tool."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A report renders in the forensic-analytics brand (Priority: P1)

A user runs `cleanmatch export` (feature 001-fairplay-analysis, User Story 4)
and opens the resulting PDF/HTML. The document looks like a high-end
forensic-analytics deliverable: dark surfaces, soft-white type, the signal-
yellow accent used sparingly on metrics and risk-window highlights, large
analytical cards for headline numbers, a minimalist timeline, and no red
anywhere. Every word the document uses is analytical, never accusatory.

**Why this priority**: This is the first place the design system is visible
to a real user, today, in the MVP. If the report looks "anti-cheat" or
uses red, the platform's "forensic, not accusatory" positioning collapses
on first contact.

**Independent Test**: Render the standard 50-game report against the design
tokens. Verify:

- Every surface colour is drawn from the locked palette (background, surface,
  border, muted, text, accent).
- No pixel in the rendered document is in the "forbidden hue range" (red 350°–
  20° saturation > 30%).
- All headline metrics use the metrics typography (size + weight + tracking).
- The vocabulary audit finds zero forbidden terms in any language.
- A non-technical reader correctly identifies it as a "forensic / analytical"
  document (≥80% in a usability test n≥5).

**Acceptance Scenarios**:

1. **Given** a completed audit run, **When** a user exports the report,
   **Then** the produced PDF and HTML use only the locked design tokens —
   no out-of-palette colour, no off-system spacing, no off-system radius.
2. **Given** a rendered report in either supported language, **When** the
   lexical audit runs, **Then** zero forbidden-terms matches are found and
   every "headline" metric uses the metrics typography spec.
3. **Given** a HIGH-risk verdict in the report, **When** the risk pill is
   rendered, **Then** it uses the locked HIGH treatment (intense yellow on
   dark surface), and not red.

---

### User Story 2 - The web product feels like a forensic analytics tool, not an anti-cheat (Priority: P2)

A first-time visitor opens the Phase 3 web UI (dashboard, audit detail,
account profile). The visual identity, copy, and motion all communicate
"analytical, precise, neutral". There are no cyberpunk glyphs, no glitch
effects, no red banners, no accusatory verbs. Risk levels are displayed in
the same locked treatment used by the PDF report so the user immediately
recognises continuity with what they exported.

**Why this priority**: The eventual web UI is the most public surface of
the platform. The brand has to read "forensic" the moment a page loads, or
the entire positioning the project is staked on (DRS §10, §13, §14) is
undermined.

**Scope note**: This feature delivers the **adapter + dynamic-audit
harness** that make the above guarantees mechanically enforceable; the
actual web pages, components, and rendered screenshots are deferred to a
follow-up feature ("Phase 3 web surfaces"). Acceptance scenarios below
are therefore expressed against the synthetic web fixture this feature
ships, not against real product pages.

**Independent Test**: Run the dynamic motion + palette + lexical audits
against `tests/fixtures/web/synthetic.html` (a single page consuming
this feature's compiled Tailwind theme + Framer Motion variants). All
three audits MUST pass with zero findings. Real-page coverage lives in
the follow-up feature's acceptance criteria.

**Acceptance Scenarios**:

1. **Given** the synthetic web fixture, **When** an automated palette
   audit inspects the rendered DOM, **Then** every colour resolves to a
   locked token and no token is "red".
2. **Given** the synthetic web fixture, **When** an automated copy audit
   scans every user-facing string, **Then** zero forbidden terms are
   found and every risk indicator uses one of the locked nouns from the
   analytical lexicon.
3. **Given** the synthetic web fixture, **When** a transition fires,
   **Then** its duration falls within 200–350 ms and its easing matches
   the locked cubic-bezier curve (no instant flicks, no neon/glitch
   motion).

---

### User Story 3 - A designer or developer can build a new surface without guessing (Priority: P3)

A contributor needs to add a new view (e.g., a heuristic-version diff
screen, or a new section in the export PDF). They open the design system
documentation and find: the locked tokens, the named components, the
canonical analytical lexicon, the preferred and forbidden words, the motion
grammar, and clear examples for every analytical card type. They build the
surface without inventing a new colour, a new corner radius, or a new
adjective.

**Why this priority**: A design system that exists only in someone's head
will rot by the third contributor. Locking it down as published, version-
controlled artefacts is what makes brand consistency a property of the
codebase rather than vigilance.

**Independent Test**: Hand a contributor the documentation and a stripped
brief ("add a panel showing the manifest"). They produce a surface that
passes both the palette audit and the lexical audit on first commit.

**Acceptance Scenarios**:

1. **Given** the design-system documentation, **When** a contributor builds
   a new surface using only the published tokens and components, **Then**
   the palette audit, typography audit, motion audit, and lexical audit all
   pass with zero violations.
2. **Given** a question "which term do we use for X?", **When** the
   contributor searches the lexicon, **Then** they find the canonical term,
   the preferred alternatives, and the explicit forbidden alternatives.

---

### Edge Cases

- **HIGH-risk surfaces**: must remain dark + signal yellow; never escalate
  to red even under stress states (server error, partial result).
- **Charting palette**: ECharts series must derive from a locked extended
  palette; no chart library may auto-pick a default series colour.
- **Internationalisation**: every forbidden-term and lexicon entry exists
  in en and pt; missing translations block release.
- **Accessibility**: signal yellow on obsidian black must pass WCAG AA for
  non-text contrast (≥3:1) and AA for small text where used as fill.
- **Print / PDF**: The design system MUST be expressible inside
  WeasyPrint's documented CSS subset for WeasyPrint 60+. The following
  features are explicitly disallowed in any token output or template
  consumed by the PDF render path:
  - CSS Grid
  - Container queries
  - `:has()` selector
  - Logical-property variants beyond `margin-*` / `padding-*`
    (`inset-block-*` etc.)
  - Subgrid
  Flexbox and CSS custom properties (`--*`) ARE permitted. Layout
  beyond flex relies on tables. Adapter compilers MUST reject token
  output that introduces any disallowed feature.
- **Reduced motion**: when the user/OS requests reduced motion, all
  transitions collapse to 0 ms; no exception.
- **Forbidden-vocabulary drift**: terms added to the lexicon's forbidden
  list MUST be retro-checked against every existing template and route.

## Requirements *(mandatory)*

### Functional Requirements

**Design tokens**

- **FR-001**: The system MUST publish a single source-of-truth design-token
  artefact in **W3C Design Tokens Community Group (DTCG) JSON**, covering:
  colour, typography, spacing, radius, shadow, motion (duration + easing),
  and z-index. The format is binding; alternative serialisations (YAML,
  TOML, vendor JSON) are rejected.
- **FR-002**: The colour token set MUST include the locked palette
  (Obsidian Black, Soft White, Signal Yellow, Neutral Gray, Dark Surface,
  Border Gray) and MUST forbid red hues. A colour is "red" iff, in HSL,
  its hue falls in `[350°, 360°] ∪ [0°, 20°]` AND its saturation exceeds
  **30 percent** (HSL saturation expressed in the 0–100 % range).
- **FR-003**: The typography token set MUST define the H1, H2, body, and
  metrics styles with size, weight, line-height, and (for metrics) letter-
  spacing matching the brief. Producers of "headline metric" numerals
  MUST tag those nodes with a stable role marker: `data-role="metric-card-headline"`
  on HTML/web surfaces and the PDF structure role `Headline-Metric` on
  PDF surfaces. The typography audit identifies headline metrics through
  these role markers; untagged metric numerals fail the audit with rule
  `missing_metric_role`.
- **FR-004**: The spacing token set MUST be exactly `{4, 8, 12, 16, 24, 32,
  48, 64}` and consuming code MUST NOT introduce off-system values.
- **FR-005**: The motion token set MUST define exactly one easing curve
  (`cubic-bezier(0.22, 1, 0.36, 1)`) and a duration range `200–350 ms`;
  values outside this range MUST require an explicit, documented override.
- **FR-006**: The radius token set MUST define four named values:
  `sm` (8 px), `md` (16 px), `lg` (24 px, **default for analytical
  surfaces**), `xl` (28 px). The `lg`/`xl` pair covers the locked
  20–28 px range for "premium / soft" treatment; `lg` is the default
  unless a component's catalogue entry explicitly requires `xl`.

**Risk-level visual language**

- **FR-007**: The system MUST define a locked visual treatment for the
  three risk levels — LOW (`color.muted` on `color.surface`), MEDIUM
  (`color.amber` on `color.surface`), HIGH (`color.signal` on
  `color.background`) — and MUST NOT use red, regardless of severity.
  Token names are the binding contract; "intense yellow" in HIGH
  resolves to the same token as the platform's Signal Yellow CTA colour
  (`color.signal`).
- **FR-008**: The same locked risk treatments MUST be used in every
  surface that displays risk: report PDF, report HTML, web dashboard,
  web audit detail, web account profile. Producers MUST tag every risk
  indicator with a stable role marker: `data-role="risk-pill"` on
  HTML/web and the PDF structure role `Risk-Pill` on PDF. The palette
  audit identifies risk indicators through these role markers and
  asserts their resolved foreground/background/border match exactly one
  of the three locked `RiskTreatment` recipes; untagged risk indicators
  fail with rule `missing_risk_role`, and tagged indicators whose
  tokens drift from a recipe fail with rule
  `risk_treatment_non_canonical`.

**Component lexicon**

- **FR-009**: The system MUST publish a named component catalogue with at
  minimum: Analytical Card (with metric, supporting line, mini-chart),
  Risk Pill, Timeline (with regions, heatmap, ply markers), Heuristic
  Badge (signal name + version), Manifest Block, and Code/Hex Inline.
- **FR-010**: Each catalogue entry MUST list its tokens-of-record (colour,
  spacing, radius, typography) and its accessibility requirements.

**Vocabulary**

- **FR-011**: The system MUST publish a canonical analytical lexicon
  containing at least: Behavioral Signal, Statistical Irregularity,
  Complexity Correlation, Tactical Precision Burst, Risk Window,
  Analytical Confidence. Each entry MUST define what it means and where
  it is appropriate.
- **FR-012**: The system MUST publish a forbidden-vocabulary list with at
  least: "cheater", "cheating", "cheat detected", "trapaceiro", "trapaça",
  "guilty", "fraud", "fraudster", "criminal", "confirmed cheating". The
  list is per-language (en, pt) and exists at the path declared by
  feature 001-fairplay-analysis (`tests/fixtures/forbidden-terms/{en,pt}.txt`).
  When this design system adds a term, it MUST be added to that file in
  the same change.
- **FR-013**: Every user-facing surface delivered by this feature
  (report PDF, report HTML, synthetic web fixture from US2) MUST pass
  the lexical audit (zero matches against the forbidden list) before
  release. Real Phase-3 web surfaces (dashboard, audit detail, account
  profile) inherit this requirement as part of the follow-up "Phase 3
  web surfaces" feature; the audit pipeline is the same, only the
  consumed artefacts differ.

**Motion & accessibility**

- **FR-014**: Animations MUST respect `prefers-reduced-motion`; when
  requested, all transitions MUST be 0 ms.
- **FR-015**: Signal Yellow on Obsidian Black MUST achieve non-text
  contrast ≥3:1 (WCAG AA non-text) and text-on-background MUST achieve
  ≥4.5:1 (WCAG AA small text); the design system MUST document the exact
  contrast ratios for each token pair.

**Versioning & enforcement**

- **FR-016**: The design system MUST carry a semantic version. Breaking
  visual changes (palette swap, removed token, removed lexicon entry) are
  MAJOR; additions are MINOR; tweaks are PATCH. The version is embedded in
  the reproducibility manifest of every rendered report
  (feature 001-fairplay-analysis FR-015).
- **FR-017**: A CI gate MUST run on every change that touches a user-
  facing surface and MUST execute, at minimum: palette audit, typography
  audit, motion audit, lexical audit. Any audit **finding of severity
  `block`** fails the gate and blocks merge. Findings of severity `warn`
  (e.g., the documented backwards-compat case in
  `contracts/manifest-field.md` for legacy manifests missing
  `design_system_version`) are surfaced in the CI summary but do not
  block merge. The set of warn-only rules is closed and enumerated in
  the audit contracts; no new warn-only rule may be added without a
  spec amendment.

### Key Entities *(include if feature involves data)*

- **DesignToken**: a named atomic value (colour hex, font size, easing
  curve, etc.) with semantic name, category, value, and version-of-
  introduction.
- **Component**: a named, reusable surface (Analytical Card, Risk Pill,
  Timeline, etc.) defined by its tokens-of-record and accessibility
  requirements.
- **LexiconEntry**: a canonical analytical term with definition, usage
  context, preferred alternatives, and forbidden alternatives.
- **ForbiddenTerm**: a word or phrase that MUST NOT appear in any user-
  facing surface, with language, category (accusation / verdict / slur),
  and matching mode (`word_boundary | substring`). Source-of-truth lives
  at `tests/fixtures/forbidden-terms/{en,pt}.txt` (declared by feature
  001-fairplay-analysis).
- **RiskTreatment**: a locked visual recipe for a categorical risk level
  (LOW / MEDIUM / HIGH) covering background, foreground, border, pill copy.
- **DesignSystemVersion**: a semver identifier embedded in every rendered
  report's reproducibility manifest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pixels in any rendered PDF or HTML report are drawn
  from the locked palette tokens (verified by a per-pixel palette audit
  with a 1% per-page tolerance for anti-aliased fringe pixels only).
- **SC-002**: Zero forbidden-term matches in any rendered surface in any
  supported language (en, pt), enforced in CI.
- **SC-003**: 100% of risk indicators across all surfaces use the locked
  RiskTreatment recipe for their level. No surface uses red on any risk
  indicator.
- **SC-004**: All transitions on every page measured in QA fall within
  200–350 ms and use the locked easing curve; when reduced-motion is
  requested, all transitions measure 0 ms.
- **SC-005**: WCAG AA contrast holds for every token pair the design
  system designates as "text on background" (≥4.5:1) and "non-text
  indicator on background" (≥3:1). The audit table is published with the
  design system.
- **SC-006**: In a usability test (n≥5 non-technical readers), ≥80%
  describe the rendered report as "analytical" or "forensic" and 0%
  describe it as "anti-cheat" or "accusatory" when asked unprompted.
- **SC-007**: A new contributor, given the design-system documentation and
  a "build a new panel" brief, ships a surface that passes the palette,
  typography, motion, and lexical audits on first commit (measured across
  ≥3 contributor onboarding events).
- **SC-008**: The design-system version is recorded in the reproducibility
  manifest of every rendered report; an audit of every recent report
  shows a non-empty `design_system_version` field.

## Assumptions

- **Primary font is Inter**; Manrope is documented as an acceptable
  fallback when Inter is unavailable for licensing reasons. Both share
  metrics close enough to keep the typography tokens stable.
- **Dark mode only** in the MVP. A light-mode variant is deferred until a
  later phase; if introduced, it MUST be added as a new token theme and
  MUST preserve the same risk semantics (still no red).
- **Languages supported**: English and Portuguese in the MVP, matching
  feature 001-fairplay-analysis. Additional languages add lexicon files
  alongside the existing en/pt files.
- **Motion-audit CI gating**: the dynamic motion audit (Playwright,
  task T067) is environment-gated by `CLEANMATCH_WEB_AUDIT=1` in MVP
  because there is no real web surface to audit yet — the synthetic
  web fixture exercises the harness, but the gate prevents Playwright
  from running on every PR in CI. FR-014's MUST clause is satisfied
  today by the static-CSS audit (T039) on the WeasyPrint adapter and
  by the zero-motion unit test under T098. When the Phase-3 web
  surfaces feature lands, the env-gate is removed and the dynamic
  audit becomes default-on.
- **Stack alignment**: the eventual web implementation will use the user-
  prescribed stack (Next.js + Tailwind + shadcn/ui + Apache ECharts +
  Framer Motion + Lucide), but the spec itself does not require any
  specific framework — only that the framework chosen can express every
  locked token. This keeps the design system implementation-agnostic and
  reusable by the PDF render path (WeasyPrint) and any future surface.
- **Source-of-truth location**: design tokens are checked into the repo at
  a path to be chosen in `/speckit-plan`; the lexicon files are colocated
  with the forbidden-terms fixtures already declared by feature 001.
- **Charting**: a small extended palette (≤6 series colours, derived from
  Signal Yellow + Neutral Gray family, never red) accompanies the main
  palette and is published alongside the tokens.
- **No red, anywhere**: this is the single inviolable rule. Stress states
  (errors, alerts, destructive confirmations) use yellow + dark contrast,
  or grayscale; never red.
- **Implementation-agnostic spec**: the WHAT lives here; the HOW (token
  file format, Tailwind config, shadcn theme, Framer Motion variants, PDF
  CSS) is planned in `/speckit-plan`.
