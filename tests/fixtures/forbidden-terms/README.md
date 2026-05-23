# Forbidden terms

Per-language TSV files driving the lexical audit (feature 001 SC-008
and feature 002 FR-013).

Format: `term\tcategory\tmatch_mode`

- `category`: `accusation` | `verdict` | `slur`
- `match_mode`: `word_boundary` | `substring`

Comment lines start with `#`. The first comment line MUST be
`# version: <semver>` so the audit can record the list version.
