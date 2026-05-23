# CLI Contract: `cleanmatch show`

**Maps to**: User Story 3 (P3) — move-level explainability
**Functional Requirements**: FR-005, FR-006, FR-008, FR-009, FR-010, FR-012,
FR-014, FR-019

## Synopsis

```text
cleanmatch show <run-id> [game-index]
    [--ply N]                          # focus on a specific ply
    [--format human|json]              # default: human
    [--language en|pt]
    [--log-format pretty|json]
    [--log-level debug|info|warn|error]
```

`<run-id>` is the UUID emitted by `audit-game` / `audit-username`.
`[game-index]` is required if the run is a username batch (0-based).
`--ply` narrows the output to a single move's drill-down.

## Behavior

1. Load the persisted `AuditRun` from `~/.cleanmatch/runs/<run-id>/`.
2. If the run is a batch and no `game-index` is given, exit 1 with a list
   of valid indices and risk levels.
3. Render the requested view.

## Human output (no `--ply`)

A timeline of plies, one line per move:

```text
Run 8f2a9e6c   Magnus_Carlsen (white)   Stockfish 16.1 depth=18 multipv=5

ply  move      ▲eval   class       complexity  flag  signals
─────────────────────────────────────────────────────────────
  1  e4        +0.32   book        0.05        ·     —
  2  e5        +0.30   book        0.06        ·     —
…
 23  Nxe6      +0.05→+1.84  brilliant   0.92        ★   engine-correlation, complexity-weighted-match
 24  Qd7       +1.78   only-move   1.00        ·     — (forced, low weight)
…

Risk level: HIGH (score 0.74, CI 0.66–0.81). See `cleanmatch show <run> --ply 23` for detail.
```

## Human output (`--ply N`)

A focused panel:

```text
Ply 23   Nxe6   played by white (Magnus_Carlsen, used 14.2 s)

Position complexity: 0.92  (branching=4.1  volatility=0.81  tactical_density=0.88)
Engine top moves (multipv=5):
  1.  Nxe6  +1.84   pv: Nxe6 fxe6 Qxh7+ …    ← played
  2.  Bxh6  +0.62   pv: Bxh6 gxh6 Qg4+ …
  3.  Re1   +0.05
  4.  Rfd1 −0.04
  5.  h3   −0.12

Signal contributions:
  engine-correlation@0.2.0          value=1.00  weight=0.92  "matched the unique top engine line"
  complexity-weighted-match@0.1.4   value=0.92  weight=0.92  "match in a highly complex position"

This move was a contributing factor to the HIGH risk classification.
It is not, by itself, evidence of cheating.
```

## JSON output

A serialised `Position` plus its `Move`, both per the data-model schema.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | User error (run not found, invalid game-index, ply out of range). |
| 2 | Upstream failure (run directory exists but is corrupt / unreadable). |
| 3 | Internal bug. |

## Examples

```bash
cleanmatch show 8f2a9e6c
cleanmatch show 8f2a9e6c --ply 23
cleanmatch show 8f2a9e6c 7 --format json
```
