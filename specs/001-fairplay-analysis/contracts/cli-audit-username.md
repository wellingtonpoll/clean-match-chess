# CLI Contract: `cleanmatch audit-username`

**Maps to**: User Story 2 (P2) — username batch audit
**Functional Requirements**: FR-002, FR-003, FR-004…FR-011, FR-015, FR-017,
FR-018, FR-019

## Synopsis

```text
cleanmatch audit-username <username>
    --platform chesscom                # only supported value in MVP
    [--count 20]                       # most recent N public games
    [--time-control bullet,blitz,rapid,classical]
    [--depth 18]
    [--multipv 5]
    [--book ~/.cleanmatch/books/master.bin]
    [--output human|json]
    [--language en|pt]
    [--log-format pretty|json]
    [--log-level debug|info|warn|error]
    [--no-cache]
    [--max-concurrency N]              # default: cpu_count
    [--debug]
```

## Behavior

1. Resolve the user against `chess.com` Public API
   (`/pub/player/{username}/games/archives` → most recent N games across
   monthly archives). Apply `--time-control` filter if present.
2. For each fetched game, run the same pipeline as `audit-game`,
   parallelised up to `--max-concurrency` (one Stockfish worker per slot).
3. Persist each per-game run independently under `runs/`.
4. Build an `AccountProfile` aggregating per-game scores and emit a single
   profile output.

## Rate limiting / resumption

- 429 / 5xx responses trigger exponential backoff (1 s, 2 s, 4 s, 8 s, 16 s)
  up to 3 retries per request.
- Already-completed per-game runs (matched by manifest cache key) are NOT
  re-fetched or re-analysed unless `--no-cache` is set.
- Ctrl-C is honoured cleanly: in-flight game analysis finishes, scheduled
  games are abandoned, and the partial profile is persisted with
  `status=partial`.

## Output: `--output human`

Stderr: progress lines (`[7/20] analysed Magnus_Carlsen vs hikaru …`).

Stdout (final block):

```text
Account profile: Magnus_Carlsen   (chess.com)
Games audited:   20 / 20 requested
Aggregate score: 0.18   (95% CI 0.11–0.27)
Risk level:      LOW

Per-game distribution:
  HIGH risk:   0
  MEDIUM risk: 2  (run-ids: 5af…, 9c1…)
  LOW risk:    18

Cross-game patterns:
  - "regime shifts in conversion phase" present in 2/20 games

This is a probabilistic assessment, not an accusation. See report for evidence.
```

## Output: `--output json`

```json
{
  "profile": {
    "username": "Magnus_Carlsen",
    "platform": "chesscom",
    "games_audited": 20,
    "aggregate_score": { "score": 0.18, "risk_level": "low", "confidence_interval": [0.11, 0.27] },
    "per_game_scores": [ { "run_id": "…", "score": 0.74, "risk_level": "high" }, "…" ],
    "cross_game_patterns": [ { "name": "regime-shift-conversion", "support": 0.1, "evidence_runs": ["…"] } ]
  }
}
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success or partial-success (user signalled stop). |
| 1 | User error (unknown username syntax, unsupported platform, invalid flags). |
| 2 | Upstream failure (network down after retries, chess.com permanent 5xx). |
| 3 | Internal bug. |

## Examples

```bash
cleanmatch audit-username hikaru --count 20
cleanmatch audit-username hikaru --count 50 --time-control blitz,rapid --output json
```
