# CLI Contract: `cleanmatch export`

**Maps to**: User Story 4 (P4) — auditable report bundle export
**Functional Requirements**: FR-013, FR-014, FR-015, FR-017, FR-019

## Synopsis

```text
cleanmatch export <run-id>
    [--format pdf,html,json,bundle]    # default: bundle (all three + manifest)
    [--out PATH]                       # default: ./cleanmatch-<run-id>.zip for bundle
    [--language en|pt]
    [--include-positions]              # embed per-position analysis in JSON
    [--log-format pretty|json]
    [--log-level debug|info|warn|error]
```

## Behavior

1. Load the persisted `AuditRun`. If `status` is not `complete` or
   `partial`, exit 1.
2. Render the requested format(s) using `packages/report-engine`. HTML and
   PDF share a single Jinja2 template; PDF is produced by WeasyPrint.
3. Always embed the `ReproducibilityManifest` in every format.
4. For `bundle`, produce a zip containing:

   ```text
   cleanmatch-<run-id>.zip
   ├── report.pdf
   ├── report.html
   ├── report.json
   ├── manifest.json
   └── README.txt           # how to reproduce
   ```

## Output

- `--format bundle`: writes the zip to `--out`, prints the absolute path to
  stdout, success line to stderr.
- `--format pdf|html|json`: writes the file to `--out`, prints the absolute
  path to stdout.

## Determinism

The exported PDF is byte-stable across runs given the same `run-id` and
report-engine version. The HTML render is also byte-stable (no JS, no
client-side timestamps). The integration test
`packages/report-engine/tests/test_byte_stability.py` enforces this.

## Forbidden language

The PDF, HTML, and JSON outputs MUST NOT contain any term from the
forbidden-terms list (SC-008). Enforced by
`report-engine/tests/test_lexical_audit.py`.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success; artefact(s) written. |
| 1 | User error (run not found, invalid `--format`, `--out` not writable). |
| 2 | Upstream failure (WeasyPrint missing system fonts/libraries). |
| 3 | Internal bug. |

## Examples

```bash
cleanmatch export 8f2a9e6c --out ./case.zip
cleanmatch export 8f2a9e6c --format pdf --out report.pdf
cleanmatch export 8f2a9e6c --format json --include-positions --out full.json
```
