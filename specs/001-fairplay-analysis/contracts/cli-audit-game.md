# CLI Contract: `cleanmatch audit-game`

**Maps to**: User Story 1 (P1) — single-game probabilistic audit
**Functional Requirements**: FR-001, FR-003, FR-004, FR-005, FR-006, FR-008,
FR-009, FR-010, FR-011, FR-012, FR-015, FR-017, FR-018, FR-019

## Synopsis

```text
cleanmatch audit-game <input>
    [--subject white|black]
    [--depth 18]
    [--multipv 5]
    [--book ~/.cleanmatch/books/master.bin]
    [--output human|json]              # default: human
    [--language en|pt]                 # default: en
    [--log-format pretty|json]         # default: pretty
    [--log-level debug|info|warn|error]# default: info
    [--no-cache]
    [--debug]
```

`<input>` is either a path to a `.pgn` file or `-` to read PGN from stdin.

## Behavior

1. Parse PGN; reject malformed input with a `user_error` (exit 1) that names
   the offending header/move.
2. Select the subject side from `--subject`, defaulting to the player whose
   username matches `CLEANMATCH_DEFAULT_USERNAME` if present, else white.
3. Build the `ReproducibilityManifest` from engine + heuristic versions +
   input SHA256. Compute a cache key from the manifest.
4. If a cached `AuditRun` exists for that key and `--no-cache` is not set,
   reuse its results.
5. Otherwise run analysis: engine pool → per-position analysis → segment
   detection → signal contributions → aggregation.
6. Persist the run under `${CLEANMATCH_HOME:-~/.cleanmatch}/runs/<run-id>/`.
7. Emit output per `--output`.

## Output: `--output human`

- All log/status lines go to **stderr**.
- The final result block goes to **stdout** in a fixed, parseable layout:

  ```text
  Audit run: 8f2a9e6c-…   (chess.com / standard)
  Subject:   white (Magnus_Carlsen, rating 2839)
  Engine:    Stockfish 16.1  depth=18 multipv=5 threads=1
  Heuristics: engine-correlation@0.2.0, complexity-analysis@0.1.4, …

  Suspicion score: 0.74  (95% CI 0.66–0.81)
  Risk level:      HIGH
  Dominant signals: engine-correlation, regime-shift, complexity-weighted-match

  Flagged segments:
    [moves 23-31] tactical    — sustained top-1 match on high-complexity moves
    [moves 42-46] conversion  — abrupt regime shift after a long think

  This is a probabilistic assessment, not an accusation. See report for evidence.
  ```

## Output: `--output json`

A single JSON document to **stdout** matching this schema (informally; the
authoritative schema lives in `packages/shared-types`):

```json
{
  "run_id": "8f2a9e6c-…",
  "manifest": { "...": "..." },
  "subject": { "username": "...", "color": "white", "rating": 2839 },
  "game": { "pgn_sha256": "...", "ply_count": 92 },
  "score": {
    "score": 0.74,
    "risk_level": "high",
    "confidence_interval": [0.66, 0.81],
    "dominant_signals": ["engine-correlation", "regime-shift", "complexity-weighted-match"]
  },
  "segments": [ { "...": "..." } ],
  "signals": [ { "...": "..." } ]
}
```

Logs in this mode remain on stderr (pretty by default, JSON if
`--log-format=json`).

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success; result emitted. |
| 1 | User error (invalid PGN, unknown subject, unsupported variant, malformed flag). |
| 2 | Upstream failure (Stockfish binary not found, missing opening book file). |
| 3 | Internal bug (caught exception with traceback; only visible with `--debug`). |

## Determinism

Given identical `<input>`, engine fingerprint, heuristic versions, opening
book SHA, and `--depth`/`--multipv`, the JSON output MUST be bit-identical
across runs. The integration test
`apps/cli/tests/integration/test_determinism.py` enforces this.

## Forbidden language

The human and JSON outputs MUST NOT contain any term from the forbidden-terms
list (SC-008). Enforced by `report-engine/tests/test_lexical_audit.py`.

## Examples

```bash
# Audit a local PGN file, white side, default depth/multipv.
cleanmatch audit-game game.pgn

# Audit stdin PGN, request JSON output for piping.
cat game.pgn | cleanmatch audit-game - --output json

# Reanalyse from scratch, bypassing the cache.
cleanmatch audit-game game.pgn --no-cache
```
