# Feature Specification: Probabilistic Fair Play Analysis Platform

**Feature Branch**: `001-fairplay-analysis`

**Created**: 2026-05-23

**Status**: Draft

**Input**: User description: "Plataforma de Análise Probabilística de Fair Play para Xadrez Online — DRS completo (visão, escopo, RF-01..RF-14, RNF-01..RNF-08, princípios constitucionais 1–8, roadmap 4 fases)"

## Clarifications

### Session 2026-05-23

- Q: What thresholds on the [0,1] suspicion score map to the categorical risk levels? → A: `low < 0.35`, `medium [0.35, 0.70)`, `high ≥ 0.70`.
- Q: What is the binding determinism contract when a third party re-runs an audit with the same manifest? → A: Bit-identical on same architecture; documented numerical tolerance (±1 cp on raw eval, ±0.001 on aggregated score) across architectures.
- Q: What is the binding composition of the SC-002 reference dataset? → A: Mixed — ≥50% selective/partial-assistance + remainder full-engine on the assisted side; clean side drawn from human rated pools in the same time-control band.
- Q: Which opening-book identity binds Principle 6 and SC-007? → A: Lichess Masters Polyglot book, ≥2400 Elo filter, depth 20 plies, SHA256-pinned in the reproducibility manifest.
- Q: What is the scope of the forbidden-terms list, and where does it live? → A: Per-language curated files at `tests/fixtures/forbidden-terms/{en,pt}.txt`; each entry tagged with `category` (accusation / verdict / slur) and a matching mode (`word_boundary | substring`); versioned artefact, source-of-truth for the lexical audit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Audit a single suspect game (Priority: P1)

An aggrieved player finishes an online game they believe involved engine
assistance from their opponent. They obtain the PGN (paste or file), point the
tool at it, and ask for a probabilistic fair-play assessment. They receive a
suspicion score, a short narrative naming the specific moves/segments that
drove the score, and a self-contained report they can keep for their records
or attach to a platform fairplay submission.

**Why this priority**: This is the MVP value proposition. The platform exists
because today these players have no way to quantify or articulate their
suspicion beyond raw accuracy numbers. Without this flow there is no product.

**Independent Test**: Provide a known-clean reference game and a known
engine-assisted reference game. Run the single-game audit on each. The clean
game must produce a low-risk classification with no flagged segments; the
engine-assisted game must produce a high-risk classification with at least
one flagged segment and at least three pieces of supporting evidence per flag.

**Acceptance Scenarios**:

1. **Given** a valid PGN file for a 60-move game, **When** the user runs a
   single-game audit, **Then** they receive a suspicion score on a documented
   scale, a categorical risk level (e.g., low/medium/high), and a narrative
   listing the moves/segments that contributed most to that score.
2. **Given** a PGN with malformed headers but legal moves, **When** the user
   runs the audit, **Then** the system surfaces a clear validation error
   pinpointing the malformed field and does not attempt analysis.
3. **Given** the same PGN audited twice with the same heuristic version and
   engine version, **When** results are compared, **Then** the scores, flagged
   segments, and per-move evidence are bit-identical.
4. **Given** a game heavy in well-known opening theory (≥15 book moves),
   **When** the audit runs, **Then** the opening segment is excluded from the
   suspicion score and the report explicitly says so.

---

### User Story 2 - Audit a player's recent public games by username (Priority: P2)

An investigator (could be the aggrieved player themselves, a club moderator,
or a researcher) suspects a specific account, not just one game. They provide
a public username from the supported platform and a count of recent games to
fetch. The system pulls the public PGNs, runs the same single-game pipeline
on each, and produces an aggregated account-level profile: which games look
clean, which look suspicious, and which signals are repeated across games.

**Why this priority**: A single game is rarely enough to support a credible
report. Cross-game patterns (consistent regime shifts, repeated blunder
suppression in time-critical positions) are far more probative. This story
is the bridge between "one anecdote" and "auditable case file".

**Independent Test**: Provide a public username with at least 20 recent
public games. Run the batch audit limited to the most recent 20. Verify
that the per-game results match what the single-game flow returns for those
PGNs individually, and that the aggregated profile correctly identifies any
game flagged at high risk.

**Acceptance Scenarios**:

1. **Given** a valid public username with ≥N recent public games, **When**
   the batch audit runs with `count=N`, **Then** the system fetches exactly
   N PGNs and produces N per-game results plus one aggregated account
   profile.
2. **Given** the platform API rate-limits the fetcher mid-batch, **When** the
   limit is hit, **Then** the system pauses, respects the documented backoff,
   resumes automatically, and never loses already-analyzed results.
3. **Given** a username with fewer public games than requested, **When** the
   batch audit runs, **Then** the system reports the actual count fetched and
   proceeds with what it has rather than erroring.
4. **Given** the same username audited twice with no new games and the same
   heuristic/engine versions, **When** results are compared, **Then** the
   aggregated profile is identical.

---

### User Story 3 - Drill into a flagged game with move-level explainability (Priority: P3)

After seeing a high-risk verdict on a game, the user needs to understand
*why*. They open the game in a timeline view that pairs each move with the
metrics that influenced its weight: engine top moves at that position, the
position's complexity score, whether the move was the only good move,
whether it sits inside a detected regime shift, and any timing anomaly.
Plain-language captions explain each highlight.

**Why this priority**: Without this layer the suspicion score is a black box,
which violates the platform's constitution (Principle 2: every piece of
evidence MUST be explainable). It is also the layer that lets a moderator or
the player themselves sanity-check the result before submitting it anywhere.

**Independent Test**: Take a game that received a high-risk verdict in P1.
Open the move-level view. For every move that contributes ≥X% to the score,
verify there is at least one displayed metric value, one human-readable
caption, and a link to the constitutional principle or heuristic invoked.

**Acceptance Scenarios**:

1. **Given** a flagged game, **When** the user opens the timeline view,
   **Then** every flagged region is visually distinct from non-flagged
   regions and accompanied by a one-sentence explanation.
2. **Given** a position the user clicks on, **When** the move detail is
   shown, **Then** they see: the move played, the top engine alternatives,
   the eval delta, the position's complexity score, and which signals (if
   any) fired at that move.
3. **Given** a move that the engine considers the only legal good answer
   ("only move"), **When** that move is shown, **Then** the UI marks it as
   low-weight and the narrative explains that forced moves don't count
   against the player.

---

### User Story 4 - Export an auditable report bundle (Priority: P4)

A user wants to attach the analysis to a fairplay report on the source
platform, or archive it as evidence. They export a bundle that contains: a
human-readable report (PDF), the underlying structured data (JSON), and a
reproducibility manifest (engine version, engine settings, heuristic
versions, input PGN hash). Anyone re-running the audit with the same
manifest must produce the same results.

**Why this priority**: This is the deliverable that turns a private opinion
into a citable artifact. It is what makes the platform a *forensic* tool
(Principle 8) rather than a hot take.

**Independent Test**: Export a report for a flagged game. Hand the bundle
to a second person on a different machine. They install the tool, point it
at the manifest, re-run, and obtain a result that diffs cleanly (no
substantive differences) against the original.

**Acceptance Scenarios**:

1. **Given** a completed audit, **When** the user requests an export,
   **Then** they receive a single archive containing the PDF report, the
   raw JSON, and the manifest.
2. **Given** the manifest from an exported bundle, **When** another user
   reruns the audit on the same PGN with that manifest, **Then** on the
   same CPU architecture the new result is **bit-identical** to the
   original; on a different CPU architecture it matches within ±1 cp on
   raw engine evaluations and ±0.001 on aggregated scores (FR-017).
3. **Given** an exported PDF, **When** opened by a non-technical reader,
   **Then** every flagged segment includes plain-language wording that does
   not assert wrongdoing, only probabilistic evidence (Principles 1, 8 and
   Ethics section of the DRS).

---

### Edge Cases

- **Truncated or malformed PGN**: validation rejects with a precise error;
  no engine cycles are spent.
- **Very short games** (<10 plies, e.g., a quick resignation): the system
  declines to produce a suspicion score and explains insufficient sample.
- **Opening-heavy games**: the documented theory plies are excluded from the
  scoring window (Principle 6) and the report says how many plies were
  discounted.
- **Forced sequences** (only-move chains, mating sequences): contribute
  near-zero weight (Principle 5) and the report says so.
- **Time-pressure scrambles** (bullet/blitz endgames): timing-based signals
  are downweighted or suppressed; the report explains.
- **Source API rate limits or transient failures**: batch jobs back off and
  resume; partial results are preserved.
- **Engine crash mid-analysis**: the run is marked incomplete, partial
  artifacts are retained, and the user is told exactly which positions were
  not analyzed.
- **Username not found / no public games**: the system reports the empty
  result without producing a fabricated "low risk" verdict.
- **PGN with non-standard variants** (Chess960, atomic, etc.): the MVP
  declines analysis and explains the variant is unsupported.
- **Concurrent runs on the same input**: a deterministic cache key prevents
  duplicate analysis cost.

## Requirements *(mandatory)*

### Functional Requirements

**Ingestion**

- **FR-001**: Users MUST be able to provide a game by uploading a local PGN
  file or pasting PGN text directly.
- **FR-002**: Users MUST be able to provide a username for the supported
  platform and a count of recent public games; the system MUST fetch those
  games via the platform's public API.
- **FR-003**: The system MUST validate PGN syntax, extract headers
  (event/site/date/players/result/time control/ECO), reconstruct the full
  position sequence, and reject inputs with precise error messages on
  failure.

**Engine analysis**

- **FR-004**: For each non-trivial position the system MUST query an engine
  configured with pinned depth, threads, hash size, and MultiPV; record the
  evaluation in centipawns (or mate distance), the principal variation, and
  the top-N candidate moves at that depth.
- **FR-005**: The system MUST flag positions as critical when at least one
  of the following holds: large evaluation swing, presence of a unique "only
  move", high complexity (see FR-006), or designation as a tactical node.

**Feature extraction**

- **FR-006**: For each analyzed position the system MUST compute a
  complexity score combining at minimum: branching factor of candidate
  moves, evaluation volatility, tactical density, and move ambiguity.
- **FR-007**: The system MUST segment each game into phases
  (opening / middlegame / tactical windows / conversion / endgame) and MUST
  detect regime shifts in decision quality between segments.
- **FR-008**: The system MUST compute, per game and per segment: top-1
  engine match rate, top-3 engine match rate, and weighted engine
  correlation.
- **FR-009**: The system MUST apply complexity-weighting so that engine
  matches in difficult positions count more than engine matches in trivial
  or forced positions (Principle 7).
- **FR-010**: The system MUST run behavioral analysis to detect: bursts of
  precision, alternation between human-like and engine-like play, statistical
  inconsistency across segments, and suppression of expected blunders.

**Scoring & explainability**

- **FR-011**: The system MUST produce a probabilistic suspicion score on the
  `[0, 1]` scale, a documented confidence interval, and a categorical risk
  level for each game, and an aggregated score for a batch of games by
  username. Risk levels MUST be assigned by the locked thresholds
  `low < 0.35`, `medium [0.35, 0.70)`, `high ≥ 0.70`. Threshold values are
  themselves versioned in the heuristics scoring module and surfaced in the
  reproducibility manifest.
- **FR-012**: Every score MUST be accompanied by an explanation listing the
  contributing segments, the contributing moves, the specific signals that
  fired, and (where applicable) the constitutional principle invoked.
- **FR-013**: The system MUST never label a user as a cheater; output
  language MUST be probabilistic and forensic (Principles 1, 8; Ethics).

**Reporting**

- **FR-014**: The system MUST be able to render a human-readable report (PDF
  and machine-readable JSON), including a timeline visualisation that
  highlights flagged regions, shows the difficulty/precision correlation,
  and shows behavioral regime changes.
- **FR-015**: Every report MUST embed a reproducibility manifest: engine
  identity and version, engine settings, heuristic version(s), input PGN
  hash, and audit run timestamp.

**Auditability & versioning**

- **FR-016**: Each heuristic MUST carry a semantic version, a changelog, and
  a documented owner; analyses MUST record which heuristic versions
  contributed to their result.
- **FR-017**: Repeating an audit on the same input with the same engine and
  heuristic versions MUST produce **bit-identical scoring outputs on the
  same CPU architecture**, and MUST match within a documented numerical
  tolerance (±1 centipawn on raw engine evaluations, ±0.001 on aggregated
  scores) **across CPU architectures**. The contract values are recorded in
  the reproducibility manifest. (Principle RNF-03: auditability.)

**Privacy & safety**

- **FR-018**: The system MUST NOT collect, transmit, or require any data
  beyond the PGNs and public usernames supplied by the user; no screen,
  webcam, microphone, or device telemetry is permitted (RNF-08; DRS §13).
- **FR-019**: Reports and CLI output MUST avoid accusatory language and MUST
  always present results as probabilistic evidence requiring human review.

### Key Entities *(include if feature involves data)*

- **Game**: a single chess game identified by its PGN, with parsed
  headers, time control, result, and a sequence of positions/moves.
- **Position**: a board state at a specific ply, with engine analysis
  attached (evaluation, top-N moves, complexity score).
- **Move**: a played move, including the engine's preferred alternatives,
  evaluation delta, classification (book / good / inaccuracy / mistake /
  blunder / forced / only-move), and contributing signals.
- **Segment**: a phase of the game (opening / middlegame / tactical / conversion
  / endgame) with its own aggregate metrics and regime label.
- **Signal**: a named heuristic output (e.g., engine_correlation, ACPL,
  complexity_weighted_match, blunder_suppression, regime_shift,
  time_anomaly), versioned and weighted.
- **SuspicionScore**: per-game and per-segment probabilistic score with
  confidence interval and risk classification.
- **AuditRun**: a single execution of the pipeline on an input, recording
  engine version, engine settings, heuristic versions, input hash,
  timestamp, and result references.
- **Report**: a deliverable bundling narrative, timeline, signal details,
  and reproducibility manifest, exportable as PDF + JSON.
- **HeuristicVersion**: semver identifier for a heuristic module with
  pointers to its changelog and tests.
- **AccountProfile**: aggregation of per-game SuspicionScores for a single
  public username, with cross-game pattern indicators.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can go from "I have a PGN" to "I have a suspicion
  score with a one-paragraph narrative" in under 5 minutes wall-clock for a
  game of up to 80 plies on a single modern desktop.
- **SC-002**: On a curated reference set of at least 10 known-clean games
  and 10 known engine-assisted games, the system flags ≥90% of the assisted
  games as medium or high risk and flags ≤5% of the clean games as medium
  or high risk (Principle 3: false positives are critical failures). The
  **engine-assisted half** MUST be composed of ≥50% selective/partial-
  assistance games (engine consulted only at critical moves, mixed with
  human play) and the remainder full-engine games; the **clean half** MUST
  be drawn from human games in rated public pools within the same
  time-control band as the assisted half. The exact corpus, its provenance,
  and per-game labels are recorded under
  `tests/fixtures/sc-002/` with a versioned `corpus.json` manifest.
- **SC-003**: 100% of high-risk verdicts in an exported report are backed by
  at least one named signal, at least one cited move, and at least one
  cited principle — no unexplained flags.
- **SC-004**: Re-running an audit on the same PGN with the same engine and
  heuristic versions on the same CPU architecture produces 100% bit-identical
  scoring outputs. On a different CPU architecture, scores match within ±1 cp
  on raw evaluations and ±0.001 on aggregated scores.
- **SC-005**: A batch audit of 20 public games for a single username
  completes within 60 minutes on the reference machine, including API
  rate-limit waits.
- **SC-006**: A non-technical reader of an exported PDF can correctly
  identify in a usability test (n≥5) at least the top three flagged moves
  and the reason each was flagged, without consulting the developer.
- **SC-007**: Opening theory excluded from scoring on a benchmark of
  classical-opening games matches the **Lichess Masters Polyglot book**
  (≥2400 Elo filter, depth 20 plies, SHA256-pinned in the reproducibility
  manifest) within 95% agreement on which plies are "book" (Principle 6).
- **SC-008**: No exported report contains accusatory language. The lexical
  audit runs against per-language curated forbidden-terms files at
  `tests/fixtures/forbidden-terms/en.txt` and
  `tests/fixtures/forbidden-terms/pt.txt`. Each entry carries a `category`
  (`accusation` / `verdict` / `slur`) and a matching mode
  (`word_boundary | substring`). The audit MUST yield zero matches on every
  exported PDF, HTML, and JSON in every supported language (Principle 1;
  Ethics).

## Assumptions

- **Phase 1 MVP interface is CLI-first.** The DRS Section 9 anticipates
  FastAPI + Next.js for the eventual full platform, but the project's
  constitution (Principle III) and prior project notes place the CLI as
  the canonical user surface for Phase 1–2. A web UI is deferred to a later
  phase and is therefore out of scope for this specification.
- **Phase 1 MVP supports chess.com Public API only** for username-based
  import (FR-002). Lichess API support is planned but deferred to a
  follow-up feature, since the DRS roadmap places multi-platform breadth
  after the core pipeline is proven.
- **Reference engine is Stockfish at a pinned version, depth, MultiPV, and
  thread count** (per the constitution's performance principle). Engines
  other than Stockfish are out of scope for the MVP.
- **All analysis runs locally.** No PGN, username, or analysis artifact
  leaves the user's machine in the MVP. This makes the privacy guarantee
  (FR-018) trivially satisfiable.
- **The user is a single operator on a single machine.** Multi-user roles,
  authentication, and shared workspaces are out of scope until the Phase 3
  web platform.
- **Game variants are limited to standard chess.** Chess960 and other
  variants are explicitly out of scope for the MVP.
- **The reference dataset for false-positive measurement (SC-002) will be
  curated separately** as part of the test-data plan; this spec fixes its
  composition rules (see SC-002) but does not enumerate individual games.
- **Reports are produced in the user's language**, with at least English
  and Portuguese supported in the MVP, matching the project's primary
  audience.
- **The platform's own ethical posture is binding.** The system must never
  promote harassment, never substitute for human moderation, and must
  always state its probabilistic nature (DRS §13).
