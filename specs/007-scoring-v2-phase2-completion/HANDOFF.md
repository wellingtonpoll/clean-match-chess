# HANDOFF — Feature 007 (Maintainer Checklist)

This feature requires manual maintainer execution for three reasons:
- 6-hour wall-clock build pass (T007) is too long for CI budgets
- Engine-assisted PGN sourcing (T010) requires human curation of public ban announcements
- FPR-gate cold-cache run (T013) needs the build + corpus outputs from T007 + T010 in place

The work is otherwise fully scripted via Phase 0–1 code drops; the maintainer only kicks off the long-running operations.

---

## Block A — Real baselines (P1, ~6 hr wall-clock background)

**Owner**: maintainer with stable machine + Docker + ≥ 200 GB free disk
**Blocking**: nothing (USA is the longest-pole task; start ASAP)

### A-1 — Pre-flight (≤ 5 min)
- [ ] `sha256sum lichess_db_standard_rated_2026-04.pgn.zst` returns the same hash on two consecutive runs (archive integrity)
- [ ] `docker run --rm cleanmatch-stockfish:sf16 stockfish <<< 'quit'` greets with "Stockfish 16"
- [ ] `zstd --version` ≥ 1.5

### A-2 — Build (~6 hr wall-clock; runs in background)
- [ ] Run `quickstart.md §3` command. Pipe stderr to a log file: `... 2> /tmp/baselines-007/build.log`
- [ ] Periodically check `tail -5 /tmp/baselines-007/build.log` for progress
- [ ] If Phase-2 aborts: re-run same command with `--resume-from /tmp/baselines-007/`

### A-3 — Verify (~30 s)
- [ ] `quickstart.md §4` — empty bucket-deficit + schema valid + new sha256 captured
- [ ] Diff `jq '.buckets[].sample_size'` between old + new JSON — old is `100`, new is `≥ 1000`

### Fallback
If SF16 Docker fails to build on maintainer machine: `--stockfish-cmd "$(which stockfish)"`. Document the system Stockfish version + sha256 in `data/README.md`.

---

## Block B — Engine-assisted corpus (P1, ~1 day manual)

**Owner**: maintainer
**Blocking**: nothing (parallel-safe with Block A)

### B-1 — Source banned-account IDs (~2-4 hr browse)
- [ ] Open `https://lichess.org/forum/lichess-feedback?search=closed+for+using+outside+assistance`
- [ ] Open r/chess archive: `https://www.reddit.com/r/chess/search/?q=lichess+banned+cheating`
- [ ] Collect ≥ 25 publicly-disclosed Lichess account IDs (titled-player ban announcements are highest-value because they're well-documented)
- [ ] Save each ID + the archive.org snapshot URL of its disclosure thread

### B-2 — Fetch + commit (~30 min once IDs in hand)
- [ ] Per disclosed ID, run `quickstart.md §6` curl command
- [ ] Skip purged accounts (HTTP 404); buffer expected, target 25 PGNs after attrition
- [ ] Commit PGN bytes (source-of-truth per link-rot policy)

### B-3 — Provenance siblings (~15 min)
- [ ] Per PGN, create the `.provenance.json` sibling per `quickstart.md §6`
- [ ] The `notes` field must be the verbatim canonical sentence (copy-paste from spec.md FR-005)
- [ ] `uv run pytest tests/fpr_gate/test_provenance.py -v` — all green

### Fallback
If < 20 PGNs reachable: surface to spec author. Do NOT use synthetic engine-assisted PGNs (R7 alternative rejected).

---

## Block C — FPR-gate validation (P1, ~45 min)

**Owner**: maintainer
**Blocking**: Block A + Block B complete

### C-1 — Cold-cache gate run (~30 min)
- [ ] `rm -rf tests/fixtures/corpora/.cache` (force cold cache to prove first-time path)
- [ ] Run `quickstart.md §7`
- [ ] Capture `tests/fixtures/corpora/fpr_gate_report.json` to scratch notes

### C-2 — Regression smoke (~10 min)
- [ ] Run `quickstart.md §8`
- [ ] Screenshot the CI `fpr_gate` job failure diagnostic for the PR description

### C-3 — Determinism (~1 min)
- [ ] Run `quickstart.md §9`
- [ ] Diff must be empty

### Fallback
If `FPR > 2%` OR `TPR < 80%`: **STOP** per FR-010. Do NOT relax the gate. Open Feature 008 to investigate algorithm tuning.

---

## Block D — Docs + CHANGELOG (P2, ~2 hr)

**Owner**: maintainer (can be the spec author)
**Blocking**: Block A + Block C complete (need measured FPR/TPR + score delta to fill in placeholders)

### D-1 — CHANGELOG (~30 min)
- [ ] Edit `CHANGELOG.md` per `tasks.md T016`
- [ ] Verify no `<placeholder>` strings remain
- [ ] Verify `[2.1.0]` header has today's date

### D-2 — Package CHANGELOG + data README (~30 min)
- [ ] `tasks.md T017` + `T018`

### D-3 — Update 005 spec docs (~30 min)
- [ ] `tasks.md T019` + `T020`

### D-4 — Open PR (~30 min)
- [ ] `quickstart.md §10` (pre-PR checks)
- [ ] `quickstart.md §11` (open PR with `scoring` label)
- [ ] Embed both determinism `run.id` UUIDs in PR description
- [ ] Embed regression-smoke screenshot in PR description
- [ ] Embed pre/post score delta in PR description
