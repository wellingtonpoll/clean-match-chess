# Contract: `tokens.json` — design-token source of truth

**Maps to**: FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-015,
FR-016 of the design-system spec.

## File location

`packages/design-system/src/design_system/tokens/tokens.json`

## Format

W3C DTCG JSON. Top-level shape:

```json
{
  "$schema": "https://design-tokens.github.io/community-group/format/",
  "$metadata": {
    "version": "1.0.0",
    "name": "forensic-analytics",
    "description": "Clean Match Chess forensic analytics design system",
    "added_in": "1.0.0"
  },
  "themes": {
    "dark": {
      "color": { ... },
      "typography": { ... },
      "spacing": { ... },
      "radius": { ... },
      "shadow": { ... },
      "motion": { ... },
      "z_index": { ... },
      "chart_series": { ... }
    }
  }
}
```

## Required token names (v1.0.0)

### `color.*`

| Name | $type | $value | Notes |
|---|---|---|---|
| `color.background`     | `color`  | `#0B0B0D` | Obsidian Black |
| `color.surface`        | `color`  | `#171717` | Dark Surface |
| `color.border`         | `color`  | `#2A2A2E` | Border Gray |
| `color.muted`          | `color`  | `#A1A1AA` | Neutral Gray |
| `color.text`           | `color`  | `#F5F5F2` | Soft White |
| `color.signal`         | `color`  | `#F4D21F` | Signal Yellow |
| `color.amber`          | `color`  | `#F4B41F` | Risk MEDIUM treatment |
| `color.chart_series.1` … `color.chart_series.6` | `color` | see research §6 | Locked 6-series ordering |

### `typography.*`

| Name | $type | $value |
|---|---|---|
| `typography.h1`        | `typography` | `{ font_family: "Inter", font_weight: 700, font_size: "56px", line_height: 1.1 }` |
| `typography.h2`        | `typography` | `{ font_family: "Inter", font_weight: 600, font_size: "32px", line_height: 1.2 }` |
| `typography.body`      | `typography` | `{ font_family: "Inter", font_weight: 400, font_size: "16px", line_height: 1.5 }` |
| `typography.body_medium`| `typography` | `{ font_family: "Inter", font_weight: 500, font_size: "16px", line_height: 1.5 }` |
| `typography.metric`    | `typography` | `{ font_family: "Inter", font_weight: 700, font_size: "36px", line_height: 1.0, letter_spacing: "-0.03em" }` |

### `spacing.*`

`spacing.{1,2,3,4,5,6,7,8}` → `{4,8,12,16,24,32,48,64}` px respectively.
No other values permitted.

### `radius.*`

| Name | $value |
|---|---|
| `radius.sm`            | `8px` |
| `radius.md`            | `16px` |
| `radius.lg`            | `24px` (DEFAULT for analytical cards) |
| `radius.xl`            | `28px` |

### `shadow.*`

| Name | $value |
|---|---|
| `shadow.card`          | `0px 10px 40px rgba(0,0,0,0.12)` |

### `motion.*`

| Name | $type | $value |
|---|---|---|
| `motion.easing.standard` | `cubicBezier` | `[0.22, 1, 0.36, 1]` |
| `motion.duration.fast`   | `duration`    | `200ms` |
| `motion.duration.medium` | `duration`    | `275ms` |
| `motion.duration.slow`   | `duration`    | `350ms` |

### `z_index.*`

`base=0, dropdown=10, sticky=20, tooltip=30, overlay=40, modal=50, toast=60`

## Validation (Pydantic v2 loader)

1. Every name matches `^[a-z][a-z0-9]*(\.[a-z0-9_]+)*$`.
2. Every `color.*.$value` is `^#[0-9A-F]{6}$`. Uppercase only.
3. Forbidden-hue check passes on every colour token: `HSL.hue ∉
   [350°, 360°] ∪ [0°, 20°]` when `HSL.saturation > 30%`.
4. Every `spacing.*.$value` is in the locked set above.
5. Every `radius.*` "large" value (`lg`, `xl`) is in `[20, 28]` px.
6. Every `motion.duration.*.$value` (ms numeric) is in `[200, 350]`.
7. Exactly one `motion.easing.*` token exists; its value is the locked
   curve.

A loader violating any rule raises `TokenFileValidationError` at boot.
CI runs the loader on every PR.

## Versioning

- MAJOR: token removed, hex changed, semantic renamed.
- MINOR: new tokens added.
- PATCH: descriptions / docstring fixes.

The version embedded in `$metadata.version` MUST equal the
`packages/design-system/pyproject.toml` version.

## Compile targets

The loader's output is consumed by:

- `compile_weasyprint.py` → `adapters/weasyprint/tokens.css` (MVP).
- `compile_tailwind.py` → `adapters/tailwind/theme.ts` (Phase 3).
- `compile_css_vars.py` → `adapters/css-vars/tokens.css` (Phase 3).

Every adapter MUST round-trip byte-identical output for unchanged
`tokens.json` (golden-file test).
