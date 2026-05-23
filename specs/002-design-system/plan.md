# Implementation Plan: Forensic Analytics Design System

**Branch**: `002-design-system` | **Date**: 2026-05-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-design-system/spec.md`

## Summary

Ship a single source-of-truth design-system package that locks the
forensic-analytics visual language and the analytical vocabulary across
every user-facing surface — today's PDF + HTML reports (feature 001), and
the Phase 3 Next.js web UI. The package publishes W3C DTCG JSON tokens
plus per-target adapters (WeasyPrint CSS for MVP, Tailwind v4 theme + CSS
variables + Framer Motion variants reserved for Phase 3), a canonical
component catalogue, an English-and-Portuguese analytical lexicon, and
four CI-blocking audits (palette, typography, motion, lexical) that any
PR touching a user-facing surface must pass. Risk levels (LOW / MEDIUM /
HIGH) use a locked yellow/amber/dark recipe; red is structurally absent
from the palette.

The MVP consumer is `packages/report-engine` (feature 001 US4): PDFs and
HTML reports render against the same token file and pass the same audits
as the eventual web UI. This keeps brand continuity end-to-end and avoids
parallel "report style" vs "web style" drift.

## Technical Context

**Language/Version**: Python 3.11 for the audit/lexicon/token-loader
helpers and the WeasyPrint CSS adapter (so feature 001 can consume the
design system without crossing a language boundary). TypeScript 5.x +
Tailwind v4 reserved for the Phase 3 web adapters; not built in this
phase.

**Primary Dependencies**: `pydantic` v2 (token + lexicon schemas),
`pyyaml` (no — JSON only, per FR-001 W3C DTCG), `tinycss2` (lint
WeasyPrint-compatible CSS), `colormath` (Delta-E + HSL palette audit).
Phase 3 only: `tailwindcss@4`, `@radix-ui/themes` via shadcn/ui,
`framer-motion`, `apache-echarts`, `lucide-react`.

**Storage**: Files-only in this feature. Token JSON, lexicon TSVs,
generated CSS, audit fixtures live in the repo; no DB.

**Testing**: `pytest` + `pytest-cov` for the Python helpers and audits.
Golden-file tests for the WeasyPrint CSS adapter and the matplotlib chart
palette generator. Coverage gate inherited from project constitution
Principle II: 85% line / 80% branch on `packages/design-system/src/`.

**Target Platform**: Linux + macOS dev workstations for MVP. Outputs
(PDF / HTML / generated CSS) consumed by feature 001's report-engine on
the same machines. Phase 3: modern evergreen browsers.

**Project Type**: New monorepo package — `packages/design-system/`. Two
phase-gated consumer surfaces:
1. MVP — `packages/report-engine` consumes the Python token loader + the
   generated WeasyPrint CSS + the lexicon module.
2. Phase 3 — `apps/frontend` consumes the Tailwind theme + Framer Motion
   variants + the shadcn theme (placeholders only in MVP).

**Performance Goals**:
- Palette audit on a 50-game PDF: ≤ 5 s wall-clock on the reference
  machine (8-core x86_64). Anti-aliasing fringe tolerance: 1% per page
  (matches SC-001).
- Lexical audit on the same PDF (both languages): ≤ 1 s.
- Token compile (JSON → WeasyPrint CSS + Tailwind CSS variables): ≤ 200 ms.
- All four audits running in parallel ≤ 8 s total in CI per artefact.

**Constraints**:
- No red anywhere in the palette (FR-002); the forbidden-hue audit is
  the structural guarantor.
- All tokens must be expressible in the WeasyPrint CSS subset (FR-001 +
  Edge Cases): no CSS Grid, no `:has()`, no container queries, no
  `inset-block-*`. Tokens compile to subset-clean CSS for the PDF
  adapter.
- Cross-feature contract with `001-fairplay-analysis` (FR-012, FR-016,
  Cross-feature CHK046): forbidden-terms file path, language set, and
  the reproducibility-manifest field name MUST stay synchronized.
- Dark mode only (Assumptions). Light-mode tokens out of scope.
- `prefers-reduced-motion` collapses every transition to 0 ms (FR-014).
  The PDF render path always behaves as if reduced-motion is active
  (PDFs have no animation).

**Scale/Scope**:
- ~60 tokens at v1.0.0 (palette + extended chart palette + typography +
  spacing + radius + shadow + motion + z-index).
- ~10 components in the catalogue at v1.0.0.
- Lexicon: ~20 canonical entries × 2 languages; forbidden-terms file
  grows over time but starts at ~12 entries × 2 languages.
- ~4 audit modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0.

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I   | Code Quality           | ✅ PASS | New package `packages/design-system/` inherits root `ruff` + `mypy --strict` config. Pydantic v2 models for tokens, lexicon, audit reports — typed by construction. |
| II  | Testing Standards      | ✅ PASS | Audits, token loader, WeasyPrint CSS adapter, matplotlib palette generator all get unit tests with pinned fixtures. Golden-file diffs for generated CSS. Coverage gate 85/80 applies. Lexical-audit + palette-audit failing tests added to feature 001 report-engine in lockstep (cross-package). |
| III | UX Consistency         | ✅ PASS | This feature *is* the UX-consistency mechanism — it formalises FR-019 of feature 001 (no accusatory language) into a published lexicon plus an automated gate. CLI human output is text-only and unaffected by colour tokens; the lexicon still applies to its strings. |
| IV  | Performance Reqs       | ✅ PASS | Audit performance budgets above are tight (≤ 8 s total in CI per artefact). The token compile step is amortised at build time, not request time. No new perf risk to the analysis pipeline. |

No principle violations. **Complexity Tracking table is empty.**

Re-check after Phase 1 design: ✅ still passing (see end of document).

## Project Structure

### Documentation (this feature)

```text
specs/002-design-system/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 — token format, adapter strategy, palette audit
├── data-model.md        # Phase 1 — token / lexicon / audit-report entities
├── quickstart.md        # Phase 1 — how to consume tokens in each surface
├── contracts/           # Phase 1 — schemas and audit-API contracts
│   ├── token-file-schema.md
│   ├── audit-palette.md
│   ├── audit-typography.md
│   ├── audit-motion.md
│   ├── audit-lexical.md
│   └── manifest-field.md
└── checklists/
    ├── requirements.md  # Spec quality checklist
    └── ux.md            # UX requirements quality checklist (55 items)
```

### Source Code (repository root)

```text
packages/design-system/                # NEW in this feature
├── pyproject.toml
├── src/design_system/
│   ├── __init__.py
│   ├── tokens/
│   │   ├── tokens.json               # W3C DTCG source-of-truth
│   │   ├── loader.py                 # Pydantic v2 typed loader
│   │   ├── compile_weasyprint.py     # MVP — emits WeasyPrint-subset CSS
│   │   ├── compile_tailwind.py       # Phase 3 placeholder
│   │   └── compile_css_vars.py       # Phase 3 placeholder
│   ├── components/
│   │   ├── catalogue.json            # Component catalogue, machine-readable
│   │   └── catalogue.py              # Loader + access helpers
│   ├── lexicon/
│   │   ├── entries_en.json
│   │   ├── entries_pt.json
│   │   ├── forbidden_terms.py        # bridges to tests/fixtures/forbidden-terms/{en,pt}.txt
│   │   └── lookup.py                 # canonical-term and forbidden lookup
│   ├── audits/
│   │   ├── palette.py                # FR-002, SC-001 — image / DOM pixel audit
│   │   ├── typography.py             # FR-003, SC-001
│   │   ├── motion.py                 # FR-005, SC-004
│   │   ├── lexical.py                # FR-013, SC-002 — pure-text audit
│   │   └── report.py                 # AuditReport dataclass + JSON serialiser
│   ├── manifest.py                   # FR-016, SC-008 — emits design_system_version
│   └── version.py                    # semver derived from package metadata
├── adapters/
│   ├── weasyprint/                   # MVP — CSS generated artefact + helper
│   │   ├── tokens.css                # generated from tokens.json
│   │   └── README.md
│   ├── tailwind/                     # Phase 3 placeholder
│   │   └── .gitkeep
│   ├── shadcn/                       # Phase 3 placeholder
│   │   └── .gitkeep
│   └── framer-motion/                # Phase 3 placeholder
│       └── .gitkeep
├── benchmarks/
│   └── bench_audits.py               # per-artefact audit performance
└── tests/
    ├── unit/                         # per-module unit tests
    ├── fixtures/
    │   ├── tokens-valid/             # known-good token files
    │   ├── tokens-invalid/           # known-bad (red present, off-spacing, etc.)
    │   ├── images/                   # fixture PDFs / PNGs for palette audit
    │   └── lexicon/                  # canonical EN/PT lexicon samples
    └── golden/
        └── tokens_to_weasyprint.css.expected

# Consumers updated in this feature
packages/report-engine/src/report_engine/
├── styles.py                         # NEW — imports design-system loader + adapter
├── render_html.py                    # USES design-system Jinja2 macros + CSS
├── render_pdf.py                     # USES adapters/weasyprint/tokens.css
└── ...

# Cross-feature dependency surface
tests/fixtures/forbidden-terms/        # Owned by feature 001; extended here
├── en.txt
└── pt.txt
```

**Structure Decision**: New monorepo package `packages/design-system/` —
fits the existing uv workspace layout from feature 001. The package is
Python-first because the MVP consumer (`packages/report-engine`) is
Python; Phase 3 web adapters live alongside as JSON / generated CSS
artefacts that any frontend toolchain can read without crossing a
language boundary.

The token JSON is the *only* source of truth. Every adapter is a pure
compile step from the same JSON — never a hand-edited theme. This is
what makes the cross-surface SC-001 guarantee mechanical instead of
aspirational.

## Constitution Check (Post-Design)

After laying out Phase 0 / Phase 1 artifacts, re-evaluation:

| # | Principle | Status | Notes |
|---|-----------|--------|-------|
| I   | Code Quality           | ✅ PASS | Token + lexicon + audit-report schemas are Pydantic-typed. Generated CSS is golden-file diffable. No hand-edited duplicate theme files. |
| II  | Testing Standards      | ✅ PASS | Audit modules + token loader + adapters all have dedicated test directories with pinned fixtures. Golden-file tests for compiled CSS guarantee byte-stability. |
| III | UX Consistency         | ✅ PASS | The audit pipeline (FR-017 of this feature) IS the cross-surface UX-consistency gate the constitution requires. |
| IV  | Performance Reqs       | ✅ PASS | Audit budgets above are tracked by `packages/design-system/benchmarks/bench_audits.py` and enforced in CI. |

No new violations introduced. **Complexity Tracking remains empty.**

## Complexity Tracking

> No constitution violations to justify.

(Empty.)
