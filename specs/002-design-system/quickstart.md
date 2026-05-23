# Quickstart — Forensic Analytics Design System

**Feature**: `002-design-system` · **Date**: 2026-05-23

How a contributor consumes the design system from each supported
surface, and how the four CI audits behave.

---

## 1. System prerequisites

Inherited from feature 001:

- Python 3.11+, `uv`, Stockfish 16+ (for end-to-end report tests).
- WeasyPrint system libs (`libpango`, `libcairo`) for PDF rendering.

Design-system-specific:

- Nothing extra in MVP — the package is pure Python with Pydantic v2,
  `tinycss2`, `colormath`, `pdfminer.six`, `selectolax`.
- Phase 3 only: Node 20+, pnpm, Playwright (for the motion audit).

## 2. Install

```bash
git clone <repo>
cd clean-match-chess
uv sync
uv run python -c "import design_system; print(design_system.version.__version__)"
```

Expected output: `1.0.0` (or whatever the current version is).

## 3. Load the tokens in Python (MVP path)

```python
from design_system.tokens.loader import load_tokens
from design_system.tokens.compile_weasyprint import compile_to_css

tokens = load_tokens()
css = compile_to_css(tokens)
# Write to adapters/weasyprint/tokens.css and commit. The PDF render
# uses this committed CSS — never call compile at render time.
```

The committed CSS lives at
`packages/design-system/adapters/weasyprint/tokens.css`. Report
templates `@import` it as a single line:

```css
@import url("../../design-system/adapters/weasyprint/tokens.css");
```

## 4. Render a token-clean report

Once feature 001's report-engine consumes the design system, the export
flow works unchanged:

```bash
uv run cleanmatch export <run-id> --out /tmp/case.zip
unzip /tmp/case.zip -d /tmp/case
ls /tmp/case
# report.pdf  report.html  report.json  manifest.json  README.txt
```

Open `manifest.json`. You should see:

```json
{
  "engine": { ... },
  "heuristics": [ ... ],
  "design_system_version": "1.0.0",
  ...
}
```

## 5. Run the four audits locally

```bash
# Palette audit (CSS + pixel) on the exported PDF.
uv run python -m design_system.audits.palette /tmp/case/report.pdf

# Typography audit on PDF + HTML.
uv run python -m design_system.audits.typography /tmp/case/report.pdf
uv run python -m design_system.audits.typography /tmp/case/report.html

# Motion audit on the generated static CSS (PDF/HTML scope).
uv run python -m design_system.audits.motion packages/design-system/adapters/weasyprint/tokens.css

# Lexical audit on PDF + HTML, both languages.
uv run python -m design_system.audits.lexical /tmp/case/report.pdf --languages en pt
uv run python -m design_system.audits.lexical /tmp/case/report.html --languages en pt
```

All four MUST exit 0. Any non-zero exit on any of them = the artefact
fails the brand gate.

## 6. Run the audits via pytest

```bash
uv run pytest -m "audit_palette or audit_typography or audit_motion or audit_lexical"
```

These marks are attached to feature 001's report-engine integration
tests, so the audits run automatically every time the report-engine
test suite runs.

## 7. Add a new analytical term to the lexicon

```bash
# 1. Edit packages/design-system/src/design_system/lexicon/entries_en.json
#    and entries_pt.json — keep them parallel.
# 2. Add unit tests asserting the new term resolves in both files.
# 3. If the new term replaces an accusatory alternative, also add
#    that alternative to tests/fixtures/forbidden-terms/{en,pt}.txt.
# 4. Re-run the lexical audit suite:
uv run pytest -m audit_lexical
# 5. Bump the design-system version (MINOR for additions, PATCH for
#    refinements) in packages/design-system/pyproject.toml.
```

## 8. Add a forbidden term

```bash
# 1. Append a row to BOTH tests/fixtures/forbidden-terms/en.txt and pt.txt
#    using the format: <term>\t<category>\t<match_mode>
# 2. Run the lexical audit against every existing fixture report:
uv run pytest -m audit_lexical
# 3. If any existing artefact contains the new forbidden term, fix the
#    source narrative/template (NEVER weaken the term) and re-run.
# 4. Bump the design-system version (MINOR).
```

## 9. Compile token changes

```bash
# After editing tokens.json:
uv run python -m design_system.tokens.compile_weasyprint
# Commit the updated adapters/weasyprint/tokens.css alongside tokens.json.
# CI's golden-file test will compare your committed output to a fresh
# recompile; any drift = CI red.
```

## 10. Replay an old report's audits

```bash
uv run python -m design_system audit-replay <run-id>
```

This reads the manifest's `design_system_version`, ensures the local
package matches (auto-installs if uv is allowed to), then runs all four
audits against the artefacts persisted under `~/.cleanmatch/runs/<run-id>/`.

## 11. Where to look next

- `specs/002-design-system/spec.md` — requirements & success criteria.
- `specs/002-design-system/plan.md` — architecture & package layout.
- `specs/002-design-system/research.md` — design decisions & alternatives.
- `specs/002-design-system/data-model.md` — token/lexicon/audit entities.
- `specs/002-design-system/contracts/` — token-file schema + four audit
  contracts + manifest field.
- `specs/002-design-system/checklists/ux.md` — requirements-quality
  checklist for design-system reviewers.
- `.specify/memory/constitution.md` — non-negotiables.
