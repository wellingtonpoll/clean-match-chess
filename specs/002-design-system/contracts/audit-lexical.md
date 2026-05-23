# Contract: Lexical Audit

**Maps to**: FR-011, FR-012, FR-013, SC-002 of the design-system spec
**Cross-feature**: Same audit consumed by feature 001-fairplay-analysis
SC-008. The forbidden-terms files live at
`tests/fixtures/forbidden-terms/{en,pt}.txt` and are co-owned.

## Purpose

Guarantee that no user-facing surface contains any term from the
per-language forbidden lists, in any supported language. Zero matches,
always.

## Supported sources

| Source | Extractor |
|---|---|
| PDF report                        | `pdfminer.six` text extraction |
| HTML report                       | `selectolax` text content |
| Rendered web page                 | Playwright `page.text()` (Phase 3) |
| CLI human output                  | stdout/stderr capture (feature 001) |
| JSON output                       | All string values flattened |
| Narrative templates (pre-render)  | Jinja2 source files |

## API

```python
from design_system.audits.lexical import (
    audit_text,
    audit_html,
    audit_pdf,
    audit_json,
    audit_template,
)

result = audit_pdf(
    pdf_path="report.pdf",
    languages=["en", "pt"],
    forbidden_terms_dir="tests/fixtures/forbidden-terms",
)
assert result.status == "pass"
```

## Behaviour

1. Load each `<lang>.txt` file from `forbidden_terms_dir`. Skip
   comment lines (lead with `#`). Each row: `term\tcategory\tmatch_mode`.
2. Compile regex per term:
   - `word_boundary` → `re.compile(r'\bTERM\b', re.IGNORECASE)`
   - `substring`     → `re.compile(re.escape(TERM), re.IGNORECASE)`
3. Extract text from the source artefact.
4. For each compiled regex, scan the text. Every match is a finding
   with rule `forbidden_term`, severity `block`, and the matched span
   in `location` (e.g., `report.pdf:p3:l42`).
5. Status `pass` iff zero findings; `fail` otherwise.

## Pre-render template audit

Templates are scanned too — catching forbidden terms in the *source*
rather than the *render* gives faster feedback in unit tests.

```python
result = audit_template(
    template_path="packages/report-engine/src/report_engine/templates/single_game.html",
    languages=["en", "pt"],
)
```

## Cross-language audit

When `languages=["en", "pt"]`, the audit runs both language lists
against the same source. This catches Portuguese leakage in an English
report and vice versa. Both languages MUST produce zero matches.

## Return shape

```python
class LexicalAuditReport:
    audit_name: Literal["lexical"]
    artefact: str
    languages: list[str]
    findings: list[AuditFinding]
    status: Literal["pass", "fail"]
```

## Performance budget

- PDF (50-game report, both languages): ≤ 1 s.
- HTML (same): ≤ 200 ms.
- Template scan: ≤ 50 ms per template file.

## CI wiring

```python
@pytest.mark.audit_lexical(artefact="report.pdf", languages=["en", "pt"])
def test_report_lexical(generated_report): ...

@pytest.mark.audit_lexical(artefact="report.html", languages=["en", "pt"])
def test_report_html_lexical(generated_report): ...
```

## Cross-feature contract

This audit is the implementation of:

- Feature 001 SC-008 ("lexical audit yields zero matches").
- Feature 002 FR-013 ("every user-facing surface MUST pass").

Changes to the forbidden-terms files MUST come with a regression test
ensuring no existing narrative/template/report breaks.

## Exit semantics

| Exit code | Meaning |
|---|---|
| 0 | Audit passes (zero matches) |
| 1 | Forbidden term found (CI-blocking) |
| 2 | Forbidden-terms file missing or malformed |
| 3 | Internal bug |
