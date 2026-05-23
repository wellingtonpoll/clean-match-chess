# Phase 1 Data Model — Probabilistic Fair Play Analysis Platform

**Feature**: `001-fairplay-analysis` · **Date**: 2026-05-23

All entities below live in `packages/shared-types/src/shared_types/` as
Pydantic v2 models. Fields are documented WHAT-they-are, not how-they're-
stored; persistence in MVP is JSON on disk under `~/.cleanmatch/runs/<id>/`.

Cardinalities use `1`, `0..1`, `0..N`, `1..N`.

---

## Entity overview

```text
EngineFingerprint 1───1 AuditRun N───1 Heuristic*Set
                           │
                           ├─1───1 Game ── 1───N Position ── 1───1 Move
                           │                       │
                           │                       └─1───N SignalContribution
                           │
                           ├─1───N Segment ── 1───N SignalAggregate
                           │
                           ├─1───1 SuspicionScore (per-game)
                           │
                           └─1───0..1 AccountProfile (when audit was username-batch)
                                        │
                                        └─1───N (AuditRun for each game in batch)

Report 1───1 AuditRun                 # one report bundle per run
ReproducibilityManifest 1───1 AuditRun
HeuristicVersion N───N Heuristic*Set  # versioned signal registry entries
```

---

## 1. `Game`

A single chess game derived from a PGN.

| Field | Type | Notes |
|---|---|---|
| `id`              | `UUID4`                    | Local identifier. |
| `pgn_sha256`      | `str` (hex)                | Canonical identity. |
| `source`          | `Enum{file, chesscom, paste}` | Where the PGN came from. |
| `headers`         | `dict[str, str]`           | PGN tag pairs. |
| `players`         | `tuple[PlayerRef, PlayerRef]` | white, black. |
| `result`          | `Enum{1-0, 0-1, 1/2-1/2, *}` | From `Result` tag. |
| `time_control`    | `TimeControl`              | Parsed; `category` ∈ `{bullet, blitz, rapid, classical, correspondence}`. |
| `eco`             | `str | None`               | ECO code if present. |
| `ply_count`       | `int`                      | Total plies. |
| `moves`           | `list[Move]`               | Length == `ply_count`. |
| `variant`         | `str`                      | "standard" only in MVP; rejected otherwise. |

**Validation**:
- `pgn_sha256` must match SHA256 of the canonicalised PGN (whitespace-stripped, headers sorted).
- `ply_count >= 10` to be eligible for scoring (spec edge case).
- `variant == "standard"` else the loader raises a typed error.

## 2. `PlayerRef`

| Field | Type | Notes |
|---|---|---|
| `username`        | `str | None` | Anonymisable. |
| `display_name`    | `str | None` | From PGN tag. |
| `rating`          | `int | None` | From PGN tag if present. |
| `color`           | `Enum{white, black}` | |
| `subject`         | `bool`       | Whether this player is the audit subject. |

## 3. `Position`

A board state at a given ply, with engine analysis attached.

| Field | Type | Notes |
|---|---|---|
| `ply`             | `int`            | 0-indexed from initial position. |
| `fen`             | `str`            | |
| `side_to_move`    | `Enum{white, black}` | |
| `eval_cp`         | `int | None`     | Centipawn eval from White's perspective, or `None` if mate (use `mate_in`). |
| `mate_in`         | `int | None`     | Positive: white mates in N; negative: black mates in N. |
| `top_moves`       | `list[CandidateMove]` | Length ≤ MultiPV (5 in MVP). |
| `complexity`      | `ComplexityScore`| FR-006 — branching, volatility, density, ambiguity. |
| `is_critical`     | `bool`           | FR-005. |
| `is_only_move`    | `bool`           | Principle 5. |
| `is_book`         | `bool`           | Principle 6 — Polyglot lookup. |

## 4. `CandidateMove`

| Field | Type | Notes |
|---|---|---|
| `san`             | `str`            | |
| `uci`             | `str`            | |
| `eval_cp`         | `int | None`     | |
| `mate_in`         | `int | None`     | |
| `pv`              | `list[str]`      | Principal variation in SAN. |
| `rank`            | `int`            | 1..MultiPV. |

## 5. `Move` (a move *played* in the game)

| Field | Type | Notes |
|---|---|---|
| `ply`             | `int`            | 0-indexed. |
| `san`             | `str`            | |
| `uci`             | `str`            | |
| `played_by`       | `Enum{white, black}` | |
| `time_spent_ms`   | `int | None`     | From PGN `[%clk]` if present. |
| `eval_delta_cp`   | `int`            | Eval before vs after. |
| `classification`  | `Enum{book, brilliant, best, excellent, good, inaccuracy, mistake, blunder, forced, only_move}` | Mutually exclusive. |
| `signal_contributions` | `list[SignalContribution]` | FR-012. |

## 6. `ComplexityScore`

| Field | Type | Notes |
|---|---|---|
| `branching_factor`  | `float`        | |
| `eval_volatility`   | `float`        | |
| `tactical_density`  | `float`        | |
| `move_ambiguity`    | `float`        | |
| `composite`         | `float`        | 0..1, used as weight in correlation. |

## 7. `Segment`

| Field | Type | Notes |
|---|---|---|
| `phase`           | `Enum{opening, middlegame, tactical, conversion, endgame}` | |
| `ply_range`       | `tuple[int, int]` | inclusive, exclusive. |
| `regime`          | `Enum{human_like, mixed, engine_like, undetermined}` | FR-007. |
| `signals`         | `list[SignalAggregate]` | |
| `score_contribution` | `float`     | 0..1. |

## 8. `Signal*` (registry, contributions, aggregates)

### `HeuristicVersion`

| Field | Type | Notes |
|---|---|---|
| `name`            | `str` (kebab-case) | e.g., `engine-correlation`. |
| `version`         | `str` (semver)     | |
| `git_sha`         | `str`              | |
| `owner`           | `str`              | Maintainer note. |
| `changelog_path`  | `str`              | Relative to repo root. |

### `SignalContribution` (per-move)

| Field | Type | Notes |
|---|---|---|
| `signal_name`     | `str`              | Matches `HeuristicVersion.name`. |
| `signal_version`  | `str`              | |
| `value`           | `float`            | Raw signal value at this move. |
| `weight`          | `float`            | Effective weight after complexity discount. |
| `rationale`       | `str`              | One-line plain-language reason (FR-012). |

### `SignalAggregate` (per-segment or per-game)

| Field | Type | Notes |
|---|---|---|
| `signal_name`     | `str`              | |
| `signal_version`  | `str`              | |
| `mean`            | `float`            | |
| `weighted_mean`   | `float`            | |
| `samples`         | `int`              | Plies counted. |

## 9. `SuspicionScore`

| Field | Type | Notes |
|---|---|---|
| `score`           | `float`            | 0..1. |
| `risk_level`      | `Enum{low, medium, high}` | Thresholds in `heuristics/scoring/thresholds.py`. |
| `confidence_interval` | `tuple[float, float]` | Bootstrap 95% CI. |
| `bootstrap_samples` | `int`            | 1000 in MVP. |
| `dominant_signals` | `list[str]`       | Top-3 contributing signal names. |

## 10. `AuditRun`

The unit of work the user starts and that the system records end-to-end.

| Field | Type | Notes |
|---|---|---|
| `id`              | `UUID4`            | Stable across the run directory. |
| `created_at`      | `datetime` (UTC)   | |
| `mode`            | `Enum{single_game, username_batch}` | FR-001 / FR-002. |
| `subject`         | `PlayerRef`        | Whose play is being audited. |
| `games`           | `list[UUID4]`      | Foreign keys to `Game.id`. |
| `engine`          | `EngineFingerprint`| |
| `heuristic_set`   | `list[HeuristicVersion]` | Exactly the signals run. |
| `score`           | `SuspicionScore | None` | Single-game; for batches see `account_profile`. |
| `account_profile` | `AccountProfile | None`| Present when `mode == username_batch`. |
| `status`          | `Enum{pending, running, complete, error}` | |
| `error`           | `RunError | None`  | Structured failure record if `status == error`. |

## 11. `EngineFingerprint`

| Field | Type | Notes |
|---|---|---|
| `name`            | `str`              | "Stockfish". |
| `version`         | `str`              | "16.1". |
| `binary_sha256`   | `str`              | |
| `uci_options`     | `dict[str, str|int|bool]` | Depth, Threads, Hash, MultiPV, UseNNUE. |
| `nnue_sha256`     | `str | None`       | If applicable. |

## 12. `AccountProfile`

| Field | Type | Notes |
|---|---|---|
| `username`        | `str`              | |
| `platform`        | `Enum{chesscom}`   | Lichess deferred. |
| `games_audited`   | `int`              | |
| `per_game_scores` | `list[SuspicionScore]` | aligned with `AuditRun.games`. |
| `aggregate_score` | `SuspicionScore`   | Weighted across games. |
| `cross_game_patterns` | `list[CrossGamePattern]` | e.g., "regime shifts present in 7/20 games". |

### `CrossGamePattern`

| Field | Type | Notes |
|---|---|---|
| `name`            | `str`              | |
| `description`     | `str`              | Plain language. |
| `support`         | `float`            | Fraction of games where the pattern fires. |
| `evidence_runs`   | `list[UUID4]`      | Refs to specific `AuditRun.games`. |

## 13. `Report`

| Field | Type | Notes |
|---|---|---|
| `run_id`          | `UUID4`            | FK to `AuditRun`. |
| `formats`         | `set[Enum{html, pdf, json}]` | Always all three for `export`. |
| `language`        | `Enum{en, pt}`     | MVP supported set. |
| `narrative`       | `Narrative`        | FR-012 captions + summary. |
| `manifest`        | `ReproducibilityManifest` | |

### `Narrative`

| Field | Type | Notes |
|---|---|---|
| `summary_paragraph` | `str`            | ≤300 words. |
| `flagged_segments`  | `list[FlaggedSegment]` | |
| `forbidden_terms_clean` | `bool`        | SC-008. |

### `FlaggedSegment`

| Field | Type | Notes |
|---|---|---|
| `segment`         | `Segment`          | |
| `headline`        | `str`              | One sentence. |
| `evidence`        | `list[str]`        | ≥1 cited move + ≥1 cited signal + ≥1 cited principle (SC-003). |

## 14. `ReproducibilityManifest`

| Field | Type | Notes |
|---|---|---|
| `engine`          | `EngineFingerprint`| |
| `heuristics`      | `list[HeuristicVersion]` | |
| `analysis_core_version` | `str` (semver) | |
| `report_engine_version` | `str` (semver) | |
| `python_chess_version`  | `str`        | |
| `opening_book_sha256`   | `str`        | |
| `input_pgn_sha256`      | `str`        | |
| `started_at`            | `datetime`   | UTC. |
| `host`                  | `HostInfo`   | OS, arch, CPU model, RAM. |

## 15. `RunError`

| Field | Type | Notes |
|---|---|---|
| `code`            | `Enum{user_error, upstream_error, internal_error}` | Maps to CLI exit codes 1/2/3. |
| `category`        | `str`              | e.g., "pgn_invalid", "chesscom_rate_limited". |
| `message`         | `str`              | Human, actionable. |
| `next_step`       | `str | None`       | Plain-language remediation. |

---

## State transitions for `AuditRun.status`

```text
pending ──► running ──► complete
                  └──► error
```

- `pending → running`: when worker pool picks up the run.
- `running → complete`: all positions analysed, score persisted, report
  optional and produced on demand by `cleanmatch export`.
- `running → error`: any unrecoverable failure; `error` populated; partial
  artefacts retained on disk (edge case from spec).

---

## Cross-cutting invariants

1. Every `SignalContribution.signal_version` MUST appear in
   `AuditRun.heuristic_set`.
2. Every `AuditRun.games[i]` MUST resolve to a `Game` whose `pgn_sha256`
   matches `ReproducibilityManifest.input_pgn_sha256` (for single-game
   runs) or is included in the manifest's `inputs[]` list (for batch).
3. Bit-identical inputs produce bit-identical `SuspicionScore` values
   (FR-017) — enforced by the determinism test in
   `apps/cli/tests/integration/test_determinism.py`.
4. No string in any rendered `Narrative` field matches the forbidden-terms
   list (SC-008) — enforced by a unit test in `report-engine/tests/`.
