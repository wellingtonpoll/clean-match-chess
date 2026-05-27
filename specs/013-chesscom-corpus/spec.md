# Feature 013 — chess.com banned-account corpus crawler

**Branch**: `013-chesscom-corpus` | **Status**: Active | **Owner**: cleanmatch

## Why

Feature 005 left a `Pending` item: collect ≥ 20 engine-assisted PGN fixtures with `label_confidence="high"` to enable the FPR-gate's TPR measurement. Lichess refuses to expose ban data via API, so spec 005 couldn't ship the fixtures and the gate is still untested.

**chess.com pub API does expose ban status** — verified live against the `quaiada` account, which returns `status: "closed:fair_play_violations"`. This unblocks corpus expansion entirely: any candidate username we can name, we can verify in one API call. Building a labeled corpus of N confirmed cheaters becomes an O(crawl) problem instead of an O(manual disclosure) one.

Caminho B Feature 013 (per roadmap doc): a BFS crawler seeded by known cheaters that walks the opponent graph, checks each visited user's `status`, and pulls PGNs from confirmed fair-play bans into `tests/fixtures/corpora/engine_assisted/`. The corpus then feeds Feature 014 (ML calibration) — without labeled data, the detector's weights stay at literature defaults from Regan 2011 and accuracy stays capped around 75 %.

## Functional Requirements

- **FR-001**: `ChesscomClient.get_player_profile(username)` MUST return the `/pub/player/{u}` JSON payload, `None` on 404, and raise `ChesscomError` on 5xx after retries exhausted (mirrors `_get_json` semantics).
- **FR-002**: `ChesscomClient.is_fair_play_banned(username)` MUST return `True` when `status.startswith("closed:fair_play")`, `False` for any other status, `None` for 404. `closed:abuse` / `closed:tos` MUST return `False` (different ban categories).
- **FR-003**: New table `chesscom_crawl_status` with `(username PK, status, depth_from_seed, seed_username, checked_at, games_pulled, profile_json)`. Migration `0004_chesscom_crawl.py`.
- **FR-004**: `record_visit()` MUST be idempotent — re-visiting same username updates status + checked_at, but `depth_from_seed` takes `LEAST(existing, new)` so a closer path doesn't get overwritten.
- **FR-005**: The crawler script BFS frontier MUST persist after every visit so an interrupted run (Ctrl-C, OOM, network) can `--resume` without re-querying any user. Re-visits are cheap (DB lookup, no chess.com call).
- **FR-006**: For users with `status LIKE 'closed:fair_play%'`, the crawler MUST pull up to `--per-user-limit` (default 20) most-recent PGN games and write each as `tests/fixtures/corpora/engine_assisted/<safe_username>_<game_id>.pgn` plus a sibling `<…>.provenance.json` with `label="engine-assisted"`, `label_confidence="high"`, `chesscom_username`, `chesscom_game_id`, `retrieved_at`, and the verbatim `status` value.
- **FR-007**: The crawler MUST stop at `--target-pgns` total fixtures (default 100) regardless of remaining frontier. BFS depth cap is `--depth` (default 2).
- **FR-008**: chess.com pub API requests MUST sleep ≥ 2 s between calls (~30 req/min budget under the public limit). Backoff on 429/5xx via the existing `ChesscomClient._get_json` retry schedule.

## Non-Functional Requirements

- **NFR-001** (Privacy): `tests/fixtures/corpora/engine_assisted/` is gitignored. Opponents' usernames in PGNs are public chess.com records but we don't want to bake a searchable "suspected cheaters + their opponents" artifact into the repo. Corpus stays local-only.
- **NFR-002** (Test isolation): `chesscom_client` tests use `httpx_mock` for the new endpoints. `chesscom_crawl` repository tests use real Postgres + skip cleanly when DB unreachable (mirrors feature 008 pattern).

## Success Criteria

- **SC-001**: From seed `quaiada` at depth 2, the crawler discovers ≥ 5 distinct fair-play-banned accounts and writes ≥ 30 PGNs into the corpus within an 8-hour run on a single-host laptop.
- **SC-002**: A mid-run `kill -SIGINT` followed by `--resume` produces the exact same corpus contents (no duplicates, no skipped visits) the second time.
- **SC-003**: 11 new repository tests + 8 new client tests pass deterministically against the dev Postgres.

## Out of Scope

- ML calibration / training a classifier on the corpus → Feature 014.
- Lichess-side corpus (Lichess ban status not exposed via public API).
- Cross-platform identity merging (same human on chess.com + Lichess — out of scope).
- Auto-rerunning the crawl on a schedule (manual `--resume` invocation is fine for MVP).
- Removing un-banned accounts from the corpus if a chess.com fairplay decision is reversed later (snapshot semantics: `provenance.json.retrieved_at` records the verification timestamp).
