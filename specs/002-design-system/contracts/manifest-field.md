# Contract: `design_system_version` field in the reproducibility manifest

**Maps to**: FR-016 + SC-008 of the design-system spec
**Cross-feature**: Extends feature 001-fairplay-analysis's
`ReproducibilityManifest` (declared in `packages/shared-types/src/
shared_types/report.py`).

## Purpose

Embed the design-system semver into every rendered report's
reproducibility manifest so that any artefact's brand provenance is
self-describing and audit-replayable.

## Schema change in feature 001's `ReproducibilityManifest`

Add the field:

```python
class ReproducibilityManifest(BaseModel):
    # ... existing fields ...
    design_system_version: str  # semver, sourced from packages/design-system/pyproject.toml
```

Validation:

- MUST match `^\d+\.\d+\.\d+(?:[-+].+)?$` (PEP 440 / semver-compatible).
- MUST equal `design_system.version.__version__` at the time the report
  is rendered. Mismatch → render-time `internal_error` (exit 3).

## Producer

`packages/report-engine/src/report_engine/render_pdf.py` reads
`design_system.version.__version__` at render time and writes the value
into the manifest passed to `weasyprint.HTML(...).render(...)`'s
metadata block.

## Consumer

Any tool that reads a manifest (audit replay, future "diff two reports"
tool) MUST honour the version. If the consumer's installed
design-system version differs, the consumer SHOULD warn (not fail) and
attempt the audit with the *embedded* version's locked rules.

## Backwards compatibility

- Manifests produced before this field existed remain valid; the field
  is required for new manifests only. The consumer treats missing
  `design_system_version` as `unknown` and emits a single warning
  (rule `manifest_missing_design_system_version`, severity `warn`).
- A MAJOR bump of the design-system version invalidates earlier
  manifests for the purpose of palette/typography/motion/lexical re-
  audits; the consumer surfaces this as a warning, never a hard fail.

## SC-008 enforcement

An automated check in
`packages/report-engine/tests/test_manifest_design_system_version.py`
asserts that every test-generated report's manifest contains a
non-empty `design_system_version` that matches the running package
version.

## Audit replay

`design-system audit-replay <run-id>` (CLI in this package's
`__main__.py`) loads the manifest, switches the local design-system to
the embedded version (via `uv pip install`), and re-runs the four
audits. Useful for forensic reproducibility of an older artefact.

## Exit semantics (replay CLI)

| Exit code | Meaning |
|---|---|
| 0 | All four audits pass against the embedded version |
| 1 | Audit failure (CI-blocking when run in CI) |
| 2 | Manifest missing or `design_system_version` unparseable |
| 3 | Internal bug |
