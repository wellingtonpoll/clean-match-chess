# Audits — v1.0.0

The design system ships **four** audits, each enforcing one
non-negotiable dimension of the forensic-analytics brand. Every audit
produces a deterministic JSON `AuditReport` (`status`, `findings`,
`metadata`) and exits 0 on `pass`, 1 on `fail`.

| Audit       | Module                                       | Scope                                     |
| ----------- | -------------------------------------------- | ----------------------------------------- |
| Palette     | `design_system.audits.palette`               | Generated CSS — no red hue, locked greys  |
| Typography  | `design_system.audits.typography`            | Generated CSS — locked stack + sizes      |
| Motion      | `design_system.audits.motion`                | CSS + (env-gated) live web — easing rules |
| Lexical     | `design_system.audits.lexical`               | Rendered artefact text — forbidden terms  |

The pytest plugin `design_system.audits.pytest_plugin` exposes the
four custom marks `audit_palette`, `audit_typography`, `audit_motion`,
`audit_lexical` so downstream packages can wire audit-bound tests.

---

## Palette audit

**Scope.** Every CSS file emitted by the four adapter compilers
(`compile_weasyprint`, `compile_tailwind`, `compile_css_vars`,
`compile_framer_motion`) plus any CSS the report engine renders.

**Rule.** No colour value whose HSL representation has
`hue ∈ [350°, 360°] ∪ [0°, 20°]` at `saturation > 30 %`. This is the
*structural* "no red" guarantee: even a freshly-introduced custom
property cannot smuggle red into the brand.

**How to run.**
```bash
uv run python -m design_system.audits.palette path/to/file.css
```

**Common failure modes.**
- Someone added a `--color-danger: #dc2626` to a vendored Tailwind
  preset — fix: remove it; severity is encoded by `risk-pill`, not by
  red.
- A new "warning" semantic uses red instead of amber — fix: bind to
  `color.amber` (`#F4B41F`) instead.

**No override procedure exists.** Red is structurally forbidden.

---

## Typography audit

**Scope.** Same as palette: every generated CSS file.

**Rule.** Font stack MUST resolve to the locked families (Inter for UI,
JetBrains Mono for code-inline, Source Serif Pro for narrative
prose). Sizes MUST appear in the `typography.*` namespace; ad-hoc
`font-size` values are rejected.

**How to run.**
```bash
uv run python -m design_system.audits.typography path/to/file.css
```

**Common failure modes.**
- An adapter inlined a numeric `font-size: 17px` instead of a token
  variable.
- A new component dropped to a system serif fallback ("Times New
  Roman") — fix: import the locked face.

**No override procedure.**

---

## Motion audit

**Scope.** Two modes:
1. **Static CSS** — every adapter-emitted CSS is scanned for
   `transition` / `animation` declarations. Easing MUST be
   `cubic-bezier(0.22, 1, 0.36, 1)`. Duration MUST be in `[200, 350]`
   ms.
2. **Dynamic web** (env-gated by `CLEANMATCH_WEB_AUDIT=1`) — opens a
   headless browser, asserts the live computed style respects the
   envelope. Deferred to Phase 6 polish; the harness emits a `pass`
   with the `web_audit_deferred` finding when gated.

**How to run.**
```bash
uv run python -m design_system.audits.motion path/to/file.css
CLEANMATCH_WEB_AUDIT=1 uv run pytest tests/unit/test_audit_motion_dynamic.py
```

**Common failure modes.**
- A new adapter emitted `ease-out` instead of the locked cubic-bezier
  curve.
- A 500 ms hover transition leaked in from a third-party preset.

**Override procedure (legitimate exception).** See
`docs/CONTRIBUTING.md` → "How to override motion legitimately".
Overrides expire automatically.

---

## Lexical audit

**Scope.** Any rendered artefact: HTML, PDF (extracted text), JSON
narrative, markdown.

**Rule.** No forbidden term in `tests/fixtures/forbidden-terms/<lang>.
txt` may appear in the artefact. Categories: `accusation`, `verdict`,
`slur`. Modes: `word_boundary` or `substring`. The audit fails closed:
if the language cannot be determined, both `en` and `pt` term lists
are applied.

**How to run.**
```bash
uv run python -m design_system.audits.lexical path/to/report.html
```

**Common failure modes.**
- Narrative copy used "cheater" or "trapaceiro" instead of the
  approved Behavioral-Signal phrasing.
- A PDF post-processor merged tokens and produced an accidental
  substring match — fix: change the wording.

**No override procedure.** Forbidden terms are non-negotiable.

---

## Audit replay (CLI)

`audit-replay` (in `src/design_system/__main__.py`) loads a manifest
JSON, asserts the embedded `design_system_version` matches the running
package version, and (optionally) re-runs the four audits against any
artefact paths supplied via `--target`. Exit codes follow the matrix
in `specs/002-design-system/contracts/manifest-field.md`:

| Exit | Meaning                                                  |
| ---- | -------------------------------------------------------- |
| 0    | Version match (and, if targets given, all audits pass)   |
| 1    | At least one audit failed                                |
| 2    | Manifest missing or `design_system_version` unparseable  |
| 3    | Internal bug                                             |

A version mismatch surfaces as a warning (rule
`design_system_version_drift`) but does not change the exit code; a
missing field surfaces as `manifest_missing_design_system_version`.
