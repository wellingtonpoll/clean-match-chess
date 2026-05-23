# Contract: Typography Audit

**Maps to**: FR-003, SC-001 of the design-system spec.

## Purpose

Verify that every text node on every user-facing surface uses tokens
from `typography.*` — specifically, that headline numbers ("metrics")
use the locked `typography.metric` recipe.

## Modes

### HTML / web

```python
from design_system.audits.typography import audit_html

result = audit_html(
    html_path="report.html",
    tokens=load_tokens(),
)
```

Behaviour:
1. Parse the HTML with `selectolax`.
2. For every element flagged as a "headline metric" (selector
   `.metric` or `[data-role="metric"]`), assert the computed style
   matches `typography.metric` exactly: font-family `"Inter"`,
   font-weight `700`, font-size `36px`, line-height `1.0`,
   letter-spacing `-0.03em`. Failures use rule `wrong_metric_typography`.
3. Verify every element with `[data-role="h1"]` uses `typography.h1`,
   etc. for the other roles.

### PDF

```python
from design_system.audits.typography import audit_pdf

result = audit_pdf("report.pdf", tokens=load_tokens())
```

Behaviour:
1. Extract text spans + their font/size/weight via `pdfminer.six`.
2. The report-engine emits text with explicit role markers (PDF
   `/T` attribute via `weasyprint`'s `--pdf-variant=pdf/ua-1`). Audit
   matches each role to the token recipe.
3. Failures use rule `wrong_metric_typography` or `wrong_role_typography`.

## "Headline metric" definition

A metric is "headline" iff it appears inside a component with
`data-role="metric-card-headline"` (web/HTML) or inside the PDF
structure tree marked with the role `Headline-Metric`. This is the
binding contract from FR-003 (resolving CHK017 / ambiguity A2): the
spec REQUIRES producers to emit these role markers.

Untagged metric numerals — i.e., a numeral using `typography.metric`
without the role marker on its container — fail with rule
`missing_metric_role`. A tagged node that does NOT use
`typography.metric` fails with rule `wrong_metric_typography`. Both
rules are CI-blocking.

## Return shape

```python
class TypographyAuditReport:
    audit_name: Literal["typography"]
    artefact: str
    findings: list[AuditFinding]
    status: Literal["pass", "fail"]
```

## Performance budget

- HTML: ≤ 500 ms for a 50-game report.
- PDF: ≤ 2 s for a 50-game report.

## CI wiring

```python
@pytest.mark.audit_typography(artefact="report.pdf")
def test_report_typography(generated_report): ...

@pytest.mark.audit_typography(artefact="report.html")
def test_report_html_typography(generated_report): ...
```

## Exit semantics

| Exit code | Meaning |
|---|---|
| 0 | Audit passes |
| 1 | Token mismatch found (CI-blocking) |
| 2 | Artefact missing |
| 3 | Internal bug |
