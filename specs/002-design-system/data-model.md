# Phase 1 Data Model — Forensic Analytics Design System

**Feature**: `002-design-system` · **Date**: 2026-05-23

All entities below live in `packages/design-system/src/design_system/`.
File-based artefacts (`tokens.json`, `entries_<lang>.json`,
`forbidden-terms/<lang>.txt`) are the durable form; Pydantic v2 models are
the typed in-memory representation. No DB.

Cardinalities use `1`, `0..1`, `0..N`, `1..N`.

---

## Entity overview

```text
TokenFile (1) ── 1..N DesignToken                ── 0..N TokenReference
                       │
                       └── 1 TokenCategory (colour | typography | spacing | radius | shadow | motion | z_index | chart_series)

ComponentCatalogue (1) ── 1..N Component ── 1..N TokenBinding ── 1 DesignToken

Lexicon[lang] (1) ── 1..N LexiconEntry
ForbiddenTermsFile[lang] (1) ── 1..N ForbiddenTerm

RiskTreatment (3 fixed instances: LOW, MEDIUM, HIGH) ── 1..N TokenBinding

AuditReport ── 0..N AuditFinding
DesignSystemVersion (singleton) ── consumed by ReproducibilityManifest (feature 001)
```

---

## 1. `TokenFile`

The W3C DTCG JSON file `tokens.json`. Loaded into a Pydantic model at
startup and validated.

| Field | Type | Notes |
|---|---|---|
| `version`     | `str` (semver)              | Matches `packages/design-system/pyproject.toml`. |
| `themes`      | `dict[str, ThemeBlock]`     | MVP: `{"dark": ThemeBlock}`. Light-mode added later. |
| `tokens`      | `dict[str, DesignToken]`    | Flat namespaced dict keyed by dotted path (`color.background`, `typography.h1`, …). |

**Validation**:
- Every token's name MUST match `^[a-z][a-z0-9]*(\.[a-z0-9_]+)*$`.
- Every `colour.*` token's `$value` MUST pass the forbidden-hue audit
  (hue ∉ `[350°, 360°] ∪ [0°, 20°]` at saturation > 30%).
- Every `spacing.*` token's numeric value MUST be in `{4, 8, 12, 16, 24,
  32, 48, 64}`.
- Every `radius.*` "large" token MUST be in `[20, 28]` px.
- Every `motion.duration.*` MUST be in `[200, 350]` ms.
- Exactly one `motion.easing.*` token (`standard`) with value
  `cubic-bezier(0.22, 1, 0.36, 1)`.

## 2. `DesignToken`

A single DTCG-compliant token.

| Field | Type | Notes |
|---|---|---|
| `name`        | `str`        | Dotted path. |
| `category`    | `TokenCategory` | enum. |
| `value`       | `TokenValue` | Polymorphic over `ColourValue`, `LengthValue`, `TypographyComposite`, `ShadowComposite`, `MotionComposite`. |
| `type`        | `str`        | DTCG `$type` (`color`, `dimension`, `typography`, `shadow`, `cubicBezier`, `duration`, `number`). |
| `description` | `str`        | DTCG `$description`. |
| `added_in`    | `str` (semver) | Version this token was introduced. |
| `references`  | `list[str]`  | Other token names this composite references. |

## 3. `TokenCategory` (enum)

`colour | typography | spacing | radius | shadow | motion | z_index | chart_series`

## 4. Polymorphic `TokenValue` variants

### `ColourValue`

| Field | Type | Notes |
|---|---|---|
| `hex`         | `str` (`^#[0-9A-F]{6}$`) | Uppercase. |
| `hsl`         | `tuple[float, float, float]` | Computed cache. |
| `lab`         | `tuple[float, float, float]` | Computed cache. |

### `TypographyComposite`

| Field | Type | Notes |
|---|---|---|
| `font_family` | `str`        | `"Inter"` (MVP). |
| `font_weight` | `int`        | 400 / 500 / 600 / 700. |
| `font_size`   | `str`        | px (`"48px"`) or rem. |
| `line_height` | `float`      | unitless. |
| `letter_spacing` | `str | None` | e.g., `"-0.03em"`. |

### `ShadowComposite`

| Field | Type | Notes |
|---|---|---|
| `offset_x`    | `str` | `"0px"`. |
| `offset_y`    | `str` | `"10px"`. |
| `blur`        | `str` | `"40px"`. |
| `colour`      | `str` | `"rgba(0,0,0,0.12)"`. |

### `MotionComposite`

| Field | Type | Notes |
|---|---|---|
| `duration_ms` | `int`     | Must satisfy `200 ≤ x ≤ 350`. |
| `easing_ref`  | `str`     | Token name (`motion.easing.standard`). |

## 5. `ComponentCatalogue` and `Component`

| Field | Type | Notes |
|---|---|---|
| `version`     | `str` (semver) | Matches the design-system version. |
| `components`  | `dict[str, Component]` | Keyed by component name (kebab-case). |

### `Component`

| Field | Type | Notes |
|---|---|---|
| `name`        | `str`           | `analytical-card`, `risk-pill`, `timeline`, `heuristic-badge`, `manifest-block`, `code-inline`, … |
| `description` | `str`           | One sentence. |
| `tokens_of_record` | `list[TokenBinding]` | Required tokens (colour, spacing, radius, typography). |
| `states`      | `list[str]`     | `default | hover | focus | active | disabled | loading | empty`. |
| `accessibility` | `AccessibilityRequirement` | Per-component a11y. |
| `surfaces`    | `set[Enum{pdf, html, web}]` | Which targets this component is allowed to render on. |
| `added_in`    | `str` (semver)  | When introduced. |

### `TokenBinding`

| Field | Type | Notes |
|---|---|---|
| `role`        | `str`           | e.g., `background`, `foreground`, `border`, `metric-type`. |
| `token_name`  | `str`           | Dotted path resolved via `TokenFile`. |
| `required`    | `bool`          | Default `true`. |

### `AccessibilityRequirement`

| Field | Type | Notes |
|---|---|---|
| `min_contrast_text` | `float | None` | e.g., 4.5. |
| `min_contrast_non_text` | `float | None` | e.g., 3.0. |
| `keyboard_focusable` | `bool` | |
| `aria_role`   | `str | None`    | If applicable. |

## 6. `Lexicon` + `LexiconEntry`

| Field | Type | Notes |
|---|---|---|
| `language`    | `Enum{en, pt}`  | |
| `version`     | `str` (semver)  | |
| `entries`     | `list[LexiconEntry]` | |

### `LexiconEntry`

| Field | Type | Notes |
|---|---|---|
| `term`        | `str`           | Canonical analytical term (e.g., "Behavioral Signal"). |
| `definition`  | `str`           | One sentence. |
| `context`     | `str`           | Where to use it (e.g., "narrative paragraphs", "risk pill labels"). |
| `alternatives_preferred` | `list[str]` | Synonyms also approved. |
| `alternatives_forbidden` | `list[str]` | Cross-reference to the forbidden-terms file. |

## 7. `ForbiddenTermsFile` + `ForbiddenTerm`

This file is **owned by feature 001-fairplay-analysis** (SC-008) and
**extended by this feature** (FR-012). Path:
`tests/fixtures/forbidden-terms/<lang>.txt` — tab-separated values.

| Field | Type | Notes |
|---|---|---|
| `language`    | `Enum{en, pt}`  | |
| `terms`       | `list[ForbiddenTerm]` | |
| `version`     | `str` (semver)  | Embedded in a header comment of the TSV. |

### `ForbiddenTerm`

| Field | Type | Notes |
|---|---|---|
| `term`        | `str`           | Lower-case canonical form. |
| `category`    | `Enum{accusation, verdict, slur}` | |
| `match_mode`  | `Enum{word_boundary, substring}` | |
| `added_in`    | `str` (semver) | |

## 8. `RiskTreatment`

A locked visual recipe for a categorical risk level. Exactly three
instances exist; they are constants in
`packages/design-system/src/design_system/components/risk_treatments.py`.

| Field | Type | Notes |
|---|---|---|
| `level`       | `Enum{LOW, MEDIUM, HIGH}` | |
| `bindings`    | `list[TokenBinding]` | `background`, `foreground`, `border` — token names below. |
| `metric_weight` | `int`         | 500 / 600 / 700 — HIGH forces 700. |
| `pill_copy_en` | `str`          | "Low risk" / "Medium risk" / "High risk". |
| `pill_copy_pt` | `str`          | "Risco baixo" / "Risco médio" / "Risco alto". |
| `role_marker_html` | `str`      | Always `risk-pill` (used as `data-role="risk-pill"`). |
| `role_marker_pdf`  | `str`      | Always `Risk-Pill` (PDF structure role). |

### Locked token bindings (the three recipes)

| Level  | `background`         | `foreground`     | `border`         | `metric_weight` |
|--------|----------------------|------------------|------------------|------|
| LOW    | `color.surface`      | `color.muted`    | `color.border`   | 500 |
| MEDIUM | `color.surface`      | `color.amber`    | `color.amber`    | 600 |
| HIGH   | `color.background`   | `color.signal`   | `color.signal`   | 700 |

`color.signal` (HIGH foreground) is the same token used for CTA accents
elsewhere in the system — there is no separate "intense yellow" token.

**Invariants**:
- No `RiskTreatment`'s bindings may resolve to a colour token whose hue
  falls in the forbidden range. Enforced by the palette audit.
- The palette audit MUST also identify every node tagged
  `data-role="risk-pill"` (HTML) or PDF role `Risk-Pill` and assert its
  resolved foreground / background / border match exactly one of the
  three recipes above. Untagged risk indicators fail with rule
  `missing_risk_role`; tagged-but-off-recipe indicators fail with rule
  `risk_treatment_non_canonical`.

## 9. `AuditReport` + `AuditFinding`

| Field | Type | Notes |
|---|---|---|
| `audit_name`  | `Enum{palette, typography, motion, lexical}` | |
| `artefact`    | `str`           | Path to the audited artefact. |
| `started_at`  | `datetime` (UTC) | |
| `finished_at` | `datetime` (UTC) | |
| `status`      | `Enum{pass, fail}` | |
| `findings`    | `list[AuditFinding]` | Empty on pass. |
| `tool_version`| `str` (semver)  | Design-system version. |

### `AuditFinding`

| Field | Type | Notes |
|---|---|---|
| `severity`    | `Enum{block, warn}` | Block fails CI; warn is informational. |
| `rule`        | `str`           | e.g., `forbidden_hue`, `off_spacing`, `forbidden_term`, `motion_too_fast`, `missing_metric_role`, `missing_risk_role`, `risk_treatment_non_canonical`, `wrong_metric_typography`, `wrong_role_typography`, `motion_out_of_range`, `motion_wrong_easing`, `motion_ignored_reduced_motion`, `manifest_missing_design_system_version` (warn-only), `unknown_color_literal`, `off_palette_pixels`. |
| `location`    | `str`           | Page/line/component reference. |
| `expected`    | `str`           | Locked value. |
| `actual`      | `str`           | Observed. |
| `message`     | `str`           | Human-readable. |

## 10. `DesignSystemVersion`

A singleton derived from `packages/design-system/pyproject.toml`.
Consumed by feature 001's `ReproducibilityManifest` as the new field
`design_system_version: str` (semver). The manifest schema in feature
001's `shared-types` package is extended in lockstep (Phase 2 task in
the upcoming `tasks.md`).

---

## Cross-cutting invariants

1. No `DesignToken` in the `colour` category resolves to a hue in
   `[350°, 360°] ∪ [0°, 20°]` at saturation > 30%. **Enforced by the
   palette audit on every render and on the token-file loader at boot.**
2. Every `Component.tokens_of_record` token name MUST resolve in
   `TokenFile.tokens`. **Enforced at catalogue load.**
3. Every `LexiconEntry.alternatives_forbidden` MUST appear in the
   `ForbiddenTermsFile` for the same language. **Enforced at lexicon
   load.**
4. The `ForbiddenTermsFile` schema (TSV columns + categories + match
   modes) MUST stay synchronised with feature 001 SC-008. **Enforced by
   a cross-feature contract test in `tests/e2e/test_forbidden_terms_schema.py`.**
5. The motion-token duration range and easing curve MUST be the same
   single-source values referenced by every adapter. **Enforced by the
   adapter compilers' golden-file tests.**
6. Re-compiling `tokens.json` produces byte-identical output for every
   adapter (golden-file test).
