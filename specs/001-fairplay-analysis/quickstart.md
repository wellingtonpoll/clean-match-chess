# Quickstart — Probabilistic Fair Play Analysis Platform

**Feature**: `001-fairplay-analysis` · **Date**: 2026-05-23

This walks a fresh contributor (or end user) from a clean machine to a first
successful audit of a real PGN. The MVP is a CLI; no web stack required.

---

## 1. System prerequisites

- **Python 3.11+** (check `python3 --version`).
- **Stockfish 16+** binary on PATH (or set `STOCKFISH_PATH=/abs/path/to/stockfish`).
  - Debian/Ubuntu: `sudo apt install stockfish`
  - macOS: `brew install stockfish`
- **uv** (Python workspace tool): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Optional: **WeasyPrint** system deps (`libpango`, `libcairo`) for PDF
  export. Skip if you only need JSON/HTML.

## 2. Clone and install

```bash
git clone <repo>
cd clean-match-chess

# Sync the entire workspace (apps + packages).
uv sync

# Verify the CLI is wired up.
uv run cleanmatch --help
```

You should see the four commands: `audit-game`, `audit-username`, `show`,
`export`.

## 3. First audit — a single local PGN

```bash
# Grab a sample fixture from the repo.
cp tests/fixtures/pgn/known-clean/example-clean.pgn /tmp/game.pgn

uv run cleanmatch audit-game /tmp/game.pgn
```

Expected:

- A progress line on stderr per ply analysed.
- A final result block on stdout naming the run id, suspicion score, risk
  level, and dominant signals.
- A persisted run directory under `~/.cleanmatch/runs/<run-id>/`.

Re-run the same command. The second run should finish almost instantly
because the manifest-keyed cache hits.

## 4. Drill into the result

```bash
uv run cleanmatch show <run-id>             # full timeline
uv run cleanmatch show <run-id> --ply 23    # focus on move 23 (white)
```

## 5. Export an auditable bundle

```bash
uv run cleanmatch export <run-id> --out /tmp/case.zip
unzip -l /tmp/case.zip
```

The zip contains `report.pdf`, `report.html`, `report.json`, `manifest.json`,
and `README.txt`. The PDF is byte-stable: running `export` again on the same
run produces an identical file.

## 6. Username batch audit (chess.com)

```bash
uv run cleanmatch audit-username Magnus_Carlsen --count 5
```

This fetches the 5 most recent public games and runs the same pipeline on
each, then prints an account profile. You can `show` and `export` each
per-game run individually.

## 7. Determinism sanity check

```bash
# First run, capture JSON.
uv run cleanmatch audit-game /tmp/game.pgn --output json > /tmp/a.json

# Force re-analysis and compare.
uv run cleanmatch audit-game /tmp/game.pgn --output json --no-cache > /tmp/b.json
diff /tmp/a.json /tmp/b.json     # MUST be empty
```

If `diff` shows anything, that's a constitution-Principle-II violation and
needs a bug report.

## 8. Run the test suite

```bash
uv run pytest                                   # fast tests
CLEANMATCH_E2E=1 uv run pytest -m slow          # opt-in e2e with real Stockfish
uv run pytest --cov=packages --cov-report=term  # coverage check
```

Coverage gates: ≥ 85% line, ≥ 80% branch on `packages/*/src/`.

## 9. Common knobs

| Env var | Effect |
|---|---|
| `STOCKFISH_PATH`           | Absolute path to the engine binary. |
| `CLEANMATCH_HOME`          | Override the run/cache root (default `~/.cleanmatch`). |
| `CLEANMATCH_LOG_LEVEL`     | `debug` / `info` / `warn` / `error`. |
| `CLEANMATCH_LOG_FORMAT`    | `pretty` / `json`. |
| `CLEANMATCH_DEFAULT_USERNAME` | Default subject for `audit-game` when `--subject` is omitted. |

## 10. Where to look next

- `specs/001-fairplay-analysis/spec.md` — requirements & success criteria.
- `specs/001-fairplay-analysis/plan.md` — architecture & project structure.
- `specs/001-fairplay-analysis/research.md` — stack rationale.
- `specs/001-fairplay-analysis/data-model.md` — entity reference.
- `specs/001-fairplay-analysis/contracts/` — CLI contracts (the canonical UX).
- `.specify/memory/constitution.md` — non-negotiables (code quality, testing,
  UX consistency, performance).
