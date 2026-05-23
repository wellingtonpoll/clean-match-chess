# `design-system` changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Semver scheme is locked by [FR-016](../../specs/002-design-system/spec.md).

---

## [1.0.0] — 2026-05-23

First stable release of the **Forensic Analytics Design System** for
Clean Match Chess. Every artefact rendered by the report engine from
this version onward carries `design_system_version = "1.0.0"` in its
reproducibility manifest.

### Tokens (added)

Colour
- `color.background` `#0B0B0D` — Obsidian Black, primary surface
- `color.surface` `#171717` — dark card surface
- `color.border` `#2A2A2E` — divider grey
- `color.muted` `#A1A1AA` — neutral grey
- `color.text` `#F5F5F2` — Soft White, primary text
- `color.signal` `#F4D21F` — Signal Yellow, HIGH-risk accent + CTAs
- `color.amber` `#F4B41F` — Amber, MEDIUM-risk accent
- `color.chart_series.{1..6}` — 6-step monochrome-tinted chart palette

Typography
- `typography.h1`, `typography.h2`, `typography.body`,
  `typography.body_medium`, `typography.metric`

Spacing scale
- `spacing.{1..8}` (4 → 64 px), `radius.{sm,md,lg,xl}`

Motion (locked envelope)
- `motion.easing.standard` = `cubic-bezier(0.22, 1, 0.36, 1)`
- `motion.durations.{fast,medium,slow}` ∈ `[200, 350]` ms
- PDF surface: no motion (FR-014); enforced by `test_pdf_reduced_motion.py`.

Shadow
- `shadow.card`

### Components (added)

Six v1.0.0 components published in
`src/design_system/components/catalogue.json`:

| Name              | Surfaces       | States              |
| ----------------- | -------------- | ------------------- |
| analytical-card   | pdf, html, web | default             |
| risk-pill         | pdf, html, web | default             |
| timeline          | html, web      | default, hover      |
| heuristic-badge   | pdf, html, web | default             |
| manifest-block    | pdf, html, web | default             |
| code-inline       | pdf, html, web | default             |

Each entry carries:
- tokens of record (namespaced)
- locked surfaces
- `AccessibilityRequirement` (contrast minima, aria role, focusability)
- `added_in: "1.0.0"`

### Lexicon (added)

Eleven analytical terms in
`src/design_system/lexicon/entries_{en,pt}.json`:

`Behavioral Signal`, `Statistical Irregularity`, `Complexity
Correlation`, `Tactical Precision Burst`, `Risk Window`, `Analytical
Confidence`, `Regime`, `Engine Reference`, `Bootstrap Estimate`,
`Determinism Guarantee`, `Reproducibility Manifest`. Every entry has a
parallel Portuguese version.

### Forbidden terms (extended by feature 001)

`tests/fixtures/forbidden-terms/{en,pt}.txt` v1.0.0:
- en: cheater, cheating, cheat detected, confirmed cheating, guilty,
  fraud, fraudster, criminal, verdict, convicted, accused, perpetrator
- pt: trapaceiro, trapaça, trapaça confirmada, culpado, fraude,
  fraudador, criminoso, veredicto, condenado, acusado, perpetrador,
  violação

### Audits

Four locked audits ship in CI:
- `palette` — HSL forbidden-hue rule (no red); locked greys
- `typography` — locked font families + token-driven sizes
- `motion` — easing `cubic-bezier(0.22, 1, 0.36, 1)`, duration
  `[200, 350]` ms; optional env-gated dynamic web audit
- `lexical` — no forbidden term in any rendered artefact

### Audit replay

`python -m design_system audit-replay <manifest.json>` (FR-016 +
SC-008): verifies the embedded `design_system_version`, warns on drift
or missing field (warn-only), exits 2 on missing/unparseable manifest.

### Adapters (generated artefacts committed)

- `adapters/weasyprint/tokens.css` — PDF (WeasyPrint)
- `adapters/tailwind/theme.ts` — Tailwind v3 preset
- `adapters/css-vars/tokens.css` — vanilla CSS custom properties
- `adapters/framer-motion/variants.ts` — Framer Motion variants
- `adapters/shadcn/components.json` + `README.md` — shadcn/ui pointer

### Governance

- Every change touching `src/**` requires a semver bump in
  `pyproject.toml` AND an entry in this CHANGELOG.
- Motion overrides expire automatically; see
  `docs/CONTRIBUTING.md` § "How to override motion legitimately".
- Lexicon and forbidden-terms changes are MINOR and require parallel
  en/pt updates.
