# Component catalogue — v1.0.0

Six components ship in the v1.0.0 catalogue. Each entry lists its
tokens of record, supported states, surfaces, accessibility
requirements, and a minimal example markup. The canonical machine-
readable source is `src/design_system/components/catalogue.json`; this
document is the human reading view.

---

## analytical-card

Large dark-surface card carrying a headline metric and supporting copy.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.surface`, `color.border`, `color.text`, `color.muted`, `color.signal`, `radius.lg`, `spacing.4`, `spacing.6`, `typography.metric`, `typography.body`, `shadow.card` |
| States | `default` |
| Surfaces | `pdf`, `html`, `web` |
| Accessibility | `aria_role: region`, contrast pair `color.text` on `color.surface` (≥ 7:1), no keyboard interaction |

### Example markup (HTML)
```html
<section data-role="analytical-card" aria-labelledby="card-title">
  <h2 id="card-title" data-role="metric-card-headline">0.42</h2>
  <p>Aggregated suspicion score across 18 plies.</p>
</section>
```

---

## risk-pill

Categorical risk indicator (LOW / MEDIUM / HIGH) with role marker
and monochrome glyph fallback.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.background`, `color.surface`, `color.muted`, `color.amber`, `color.signal`, `color.border`, `radius.sm`, `typography.body_medium` |
| States | `default` |
| Surfaces | `pdf`, `html`, `web` |
| Accessibility | `aria_role: status`, glyph (●/▲/■) supplements colour for colour-blind users; HTML marker `data-role="risk-pill"`, PDF tagged role `Risk-Pill` |

### Example markup (HTML)
```html
<span data-role="risk-pill" data-level="medium" aria-label="Medium risk">
  ▲ MEDIUM
</span>
```

---

## timeline

Per-ply ribbon with regime markers and complexity heatmap. The web
surface adds hover affordances; PDF emits the static variant only.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.background`, `color.surface`, `color.signal`, `color.amber`, `color.muted`, `spacing.2`, `spacing.4` |
| States | `default`, `hover` |
| Surfaces | `html`, `web` |
| Accessibility | `aria_role: list`, per-ply nodes carry `aria-label="ply N — <regime>"`, focus visible per WCAG 2.4.7 |

### Example markup (HTML)
```html
<ol data-role="timeline" aria-label="Per-ply regime ribbon">
  <li data-role="timeline-node" data-regime="opening" aria-label="ply 4 — opening"></li>
</ol>
```

---

## heuristic-badge

Signal name + version pill (e.g., `engine-correlation@0.1.0`). Used
in narrative footnotes and the manifest block.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.surface`, `color.muted`, `color.text`, `radius.sm`, `typography.body` |
| States | `default` |
| Surfaces | `pdf`, `html`, `web` |
| Accessibility | `aria_role: text`, no interaction |

### Example markup (HTML)
```html
<span data-role="heuristic-badge">engine-correlation@0.1.0</span>
```

---

## manifest-block

Tabular block listing reproducibility manifest fields. One row per
field; tokens carry the dark-surface treatment.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.surface`, `color.border`, `color.text`, `color.muted`, `spacing.3`, `typography.body` |
| States | `default` |
| Surfaces | `pdf`, `html`, `web` |
| Accessibility | `aria_role: table`, every cell has an associated header (`<th>`) |

### Example markup (HTML)
```html
<table data-role="manifest-block">
  <thead><tr><th scope="col">Field</th><th scope="col">Value</th></tr></thead>
  <tbody><tr><th scope="row">engine</th><td>stockfish 16.1</td></tr></tbody>
</table>
```

---

## code-inline

Inline monospace span for hashes, hex values, identifiers. Always
rendered in the surface colour, never tinted.

| Property | Value |
| -------- | ----- |
| Tokens of record | `color.surface`, `color.text`, `typography.body` |
| States | `default` |
| Surfaces | `pdf`, `html`, `web` |
| Accessibility | `aria_role: text` (default span semantics) |

### Example markup (HTML)
```html
Hash <code data-role="code-inline">7c1a...e29f</code> from manifest.
```

---

## Adding a new component

See `docs/CONTRIBUTING.md` → "How to add a component". Every new entry
MUST also add a unit test under
`tests/unit/test_catalogue_entries.py`.
