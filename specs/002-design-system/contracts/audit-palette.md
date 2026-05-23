# Contract: Palette Audit

**Maps to**: FR-002, FR-007, FR-013, FR-017, SC-001, SC-003 of the
design-system spec.

## Purpose

Guarantee that every user-facing rendered surface (PDF, HTML page, web
view) shows only colours derivable from the locked `tokens.json` palette
and that no surface contains a forbidden hue (no red).

## Audit modes

Two tracks, both run for every audited artefact. **Either failure blocks
merge.**

### Track A — generated-CSS lint

```python
from design_system.audits.palette import audit_generated_css

result = audit_generated_css(
    css_path="packages/design-system/adapters/weasyprint/tokens.css",
)
assert result.status == "pass"
```

Behaviour:
1. Parse the CSS with `tinycss2`.
2. Collect every literal colour token (`#xxxxxx`, `rgb(...)`,
   `rgba(...)`, `hsl(...)`).
3. Each MUST resolve to a known token in `tokens.json`. Unknown colours
   fail with rule `unknown_color_literal`.
4. The forbidden-hue check runs on every observed colour value, with the
   same `HSL hue ∈ [350°, 360°] ∪ [0°, 20°]` × `HSL saturation > 30 % (0–100 % range)` rule. Failures use rule
   `forbidden_hue`.

### Track B — pixel audit

```python
from design_system.audits.palette import audit_pdf, audit_image

pdf_result = audit_pdf(
    pdf_path="/tmp/case.pdf",
    tokens=load_tokens(),
    delta_e_threshold=5.0,
    fringe_tolerance=0.01,
)
assert pdf_result.status == "pass"

image_result = audit_image(
    image_path="screenshots/dashboard.png",
    tokens=load_tokens(),
    delta_e_threshold=5.0,
    fringe_tolerance=0.01,
)
```

Behaviour:
1. Rasterise every PDF page at 144 DPI (or load PNG screenshots
   directly).
2. Convert each pixel to Lab.
3. For each pixel, compute Delta-E to every palette colour; pass if the
   minimum Delta-E ≤ `delta_e_threshold`.
4. Allow ≤ `fringe_tolerance` × page-pixel-count anti-aliasing fringe
   failures. Above the tolerance → rule `off_palette_pixels`.
5. Independently, every pixel goes through the forbidden-hue check.
   Failures use rule `forbidden_hue`.

## Return shape

```python
class PaletteAuditReport:
    audit_name: Literal["palette"]
    artefact: str
    tracks: dict[Literal["css", "pixel"], TrackResult]
    status: Literal["pass", "fail"]
    started_at: datetime
    finished_at: datetime
    tool_version: str            # design-system semver

class TrackResult:
    status: Literal["pass", "fail", "skipped"]
    findings: list[AuditFinding]
```

### Track C — risk-indicator role check (SC-003)

Runs alongside Tracks A + B on HTML / PDF artefacts that may contain
risk indicators.

```python
from design_system.audits.palette import audit_risk_indicators

result = audit_risk_indicators(
    artefact_path="report.html",  # or report.pdf
    tokens=load_tokens(),
)
assert result.status == "pass"
```

Behaviour:
1. Locate every node tagged `data-role="risk-pill"` (HTML, via
   `selectolax`) or every PDF structure-tree element with role
   `Risk-Pill` (via `pdfminer.six`).
2. Resolve the node's computed background / foreground / border colour
   values.
3. Each tagged node MUST match exactly one of the three locked
   `RiskTreatment` recipes (LOW / MEDIUM / HIGH) — same token names,
   not merely visually similar hexes. Mismatches fail with rule
   `risk_treatment_non_canonical`.
4. If a colour pattern visually matches a risk recipe but no `risk-pill`
   role tag is present on the surrounding node, fail with rule
   `missing_risk_role` (producer error: indicator emitted without the
   contract role marker).

This track exists to satisfy SC-003 deterministically and to enforce
FR-008's producer-side role-marker contract.

## Performance budget

- Track A: ≤ 100 ms on the WeasyPrint adapter's CSS.
- Track B: ≤ 5 s for a 50-game report PDF on the reference machine.
- Track C: ≤ 500 ms per artefact (folded into Tracks B's DOM walk).

Enforced by `packages/design-system/benchmarks/bench_audits.py`.

## CI wiring

The pytest plugin exposes `@pytest.mark.audit_palette(artefact=...)`.
Feature 001's report-engine integration tests apply this mark to every
rendered fixture.

```python
@pytest.mark.audit_palette(artefact="report.pdf")
def test_report_palette(generated_report):
    ...
```

## Exit semantics (when run standalone)

```text
$ python -m design_system.audits.palette /tmp/case.pdf
```

| Exit code | Meaning |
|---|---|
| 0 | Both tracks pass |
| 1 | Track A or Track B failure (CI-blocking) |
| 2 | Artefact missing or unreadable |
| 3 | Internal bug |
