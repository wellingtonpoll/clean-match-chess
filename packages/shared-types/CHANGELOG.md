# shared-types Changelog

## Unreleased (Feature 005 Phase 2)

### Added

- `AuditRun.manifest: ReproducibilityManifest | None = None` —
  optional in-band provenance field. Defaults to None for backward
  compatibility with cached / pre-feature-005 AuditRun objects; populated
  by the analysis-core pipeline for new audits (feature 005 FR-003, US4).
