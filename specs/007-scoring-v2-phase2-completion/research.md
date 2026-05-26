# Phase 0 — Research

**Feature**: 007 Scoring v2 Phase 2 Completion
**Date**: 2026-05-25

Eight technical decisions taken before implementation. Each carries Rationale + Alternatives Considered. Decisions feed directly into `plan.md` § Technical Context and `tasks.md` T001–T025.

---

## R1 — Source month: 2026-04 (deviation from 005's `2025-06` pin)

**Decision**: Use the locally-downloaded `lichess_db_standard_rated_2026-04.pgn.zst` (28 GB compressed, sha256 captured at build time). Change `DEFAULT_MONTH` in `packages/heuristics/scripts/build_baselines.py` from `"2025-06"` → `"2026-04"`.

**Rationale**: User has already downloaded the 2026-04 archive. Re-downloading 2025-06 (another 28 GB, hours of bandwidth) would not yield meaningfully different baselines — Lichess monthly distributions are stable month-to-month (FR-001 sample size ≥ 1000 is satisfied by either). Provenance for reproducibility is preserved by the archive's sha256 (recorded in `data/README.md`), not by the month string.

**Alternatives Considered**:
- Stick with 2025-06: rejected — re-download cost + no analytical benefit
- Run both for comparison: rejected — 12 hours of CPU instead of 6, single result already meets all SC

---

## R2 — Streaming via `zstdcat` subprocess (not full decompress to disk)

**Decision**: Spawn `zstd -d -c <archive>` as subprocess; pipe stdout through `io.TextIOWrapper(proc.stdout, encoding="utf-8")` to `chess.pgn.read_game(stream)` in a loop. New helper `_stream_filtered_games(zst_path, seed)` in `build_baselines.py`.

**Rationale**: Decompressed PGN is ~170 GB; full disk decompress is disk-pressure-hostile on most maintainer machines. `chess.pgn.read_game` already supports streaming via any `read()`-able object. The existing `packages/analysis-core/src/analysis_core/ingest/pgn_loader.py::load_pgn_text` helper reads whole strings — cannot be reused without modification — so the streaming wrapper is a new helper.

**Alternatives Considered**:
- Decompress to a temp `.pgn` file first: rejected — 170 GB peak disk
- Python-native `zstandard.ZstdDecompressor`: rejected — adds package complexity vs system `zstd` (1.5.5 already installed); subprocess pipe is simpler

---

## R3 — Two-phase build (sample first, analyze second)

**Decision**: Phase 1 streams the archive once and reservoir-samples 5000 games per bucket into `/tmp/baselines-007/<bucket>.sample.pgn`. Phase 2 reads the checkpoints and runs Stockfish depth 12 over the 30 000 sampled PGN strings. A `--resume-from CHECKPOINT_DIR` flag allows Phase-2 restart without re-streaming.

**Rationale**: A single-phase loop would tie up I/O and CPU together (170 GB stream + 45 CPU-hr); a 6-hour abort (sleep, OOM) would lose all progress. Two-phase architecture caps Phase-1 at ~30 minutes and makes Phase-2 restartable. Checkpoint files are gitignored (recoverable from the seed + source archive sha256).

**Alternatives Considered**:
- Single-pass interleaved: rejected — abort-loss risk
- Periodic Phase-2 checkpoints: rejected — Stockfish analysis is per-position-stateless; the natural checkpoint boundary is "this PGN is done"

---

## R4 — Bucket keying on `min(WhiteElo, BlackElo)`, `rating-unknown` = elementwise median

**Decision**: Inherit `min(WhiteElo, BlackElo)` from `build_baselines.py:38-44` `BUCKET_DEFINITIONS`. The 7th `rating-unknown` bucket is the elementwise median of the 6 rated buckets' measured stats (matches the stub's median path at line 79-98).

**Rationale**: Lower-of-both-ratings biases analysis toward the weaker player's expected calibre, which is the conservative choice when judging suspicious play; consistent with how the stub interprets the schema's `bucket_label` enum. Median (not mean) for `rating-unknown` is robust against any one bucket having sparse data.

**Alternatives Considered**:
- Mean of both ratings: rejected — over-weights the stronger player
- `rating-unknown` = mean: rejected — single-bucket sparse data would skew it

---

## R5 — Stockfish source: SF16 via Docker (fallback `shutil.which`)

**Decision**: Default `--stockfish-cmd "docker run --rm -i cleanmatch-stockfish:sf16"`. T003 builds the image from `infra/docker/stockfish.Dockerfile`. `podman` is accepted as a drop-in for `docker` on the maintainer machine (Dockerfile + `run --rm -i` CLI work unchanged). Fallback: `shutil.which("stockfish")` if neither runtime available.

**Recorded artefacts** (this maintainer machine, 2026-05-25): podman 4.9.3, image tag `cleanmatch-stockfish:sf16`, image id `513d26669882`, Stockfish binary sha256 `0a646b82f8577a9a5a617cf062de17886637b3056a80cda93f0e260a682ef17d`.

**Rationale**: SF16 binary sha256 already stamped in `engine_binary_sha256` for any cached `tests/fixtures/corpora/.cache/` entries (from 005). Pinning SF16 keeps `.cache/` reusable and matches the FPR-gate's `actions/cache@v4` key. `EngineAnalyzer` already accepts a `list[str]` command form (`packages/analysis-core/src/analysis_core/engine/analysis.py:85-88`) — zero code change needed in the engine wrapper.

**Alternatives Considered**:
- System `stockfish` only: rejected — version drift busts existing `.cache/`
- Newer SF version: rejected — same drift problem; the FPR-gate calibration was tuned against SF16

---

## R6 — Determinism: per-instance `random.Random(seed)`, Stockfish `Threads=1, Hash=256`

**Decision**: Every RNG call routes through an explicit `random.Random(seed)` instance threaded through the call chain. Stockfish is forced to single-thread (`Threads=1, Hash=256`) — already enforced in `EngineAnalyzer.__enter__` (`packages/analysis-core/src/analysis_core/engine/analysis.py:108`).

**Rationale**: FR-004 / SC-002 require byte-identical re-runs. Module-level `random` calls inherit Python's hash-randomized seed and break determinism across processes. Stockfish multi-threading is the other well-known nondeterminism source.

**Alternatives Considered**:
- Module-level `random.seed(seed)`: rejected — leaks state across modules + still hash-randomized for `set()` iteration order
- Skip determinism: rejected — FR-004 / SC-002 are acceptance criteria

---

## R7 — Engine-assisted sourcing: Lichess API + archive.org snapshots

**Decision**: For each publicly-disclosed banned-account ID sourced from Lichess forum (`lichess.org/forum/lichess-feedback`) + r/chess archive, hit `https://lichess.org/api/games/user/<id>?max=5&tags=true`. Commit the returned PGN bytes (source-of-truth per link-rot policy). Each `.provenance.json` cites the archive.org snapshot URL of the original ban announcement plus the canonical circularity-acknowledgement sentence per FR-005.

**Rationale**: Lichess does not publish a flagged-account list; the publicly-disclosed cases (titled-player bans, high-profile cheating cases) are the only labelled ground-truth available. The TPR bound from these is exactly Lichess's classifier accuracy on its own published cases — circularity that's already acknowledged in the spec via `.provenance.json notes` per FR-005.

**Alternatives Considered**:
- chess.com banned accounts: rejected — API doesn't expose banned-account PGNs
- Synthetic engine-assisted PGNs (replay Stockfish against itself): rejected — too clean; doesn't reflect human-mixed cheating patterns
- ChessBase forensic archive: rejected — not freely redistributable

---

## R8 — CI hook: reuse existing `fpr_gate` job, no workflow changes

**Decision**: `.github/workflows/ci.yml:151-189` `fpr_gate` job is reused unchanged. Cache key (`opening_book.bin` + corpus PGN hashes) already busts on `engine_assisted/**/*.pgn` content changes. Branch-protection requirement is a maintainer concern (configured in GitHub UI, not code).

**Rationale**: The job exists and is sound. The only blocker on its activation was empty corpus directories — T010 fixes that. No need to introduce new jobs or modify the path filter.

**Alternatives Considered**:
- Add a separate `baselines_smoke` job: rejected — duplicates work; the existing job runs both signal modules
- Tighten cache invalidation: rejected — current key is already correct; the manifest `engine_binary_sha256` provides defense-in-depth for stale cache entries
