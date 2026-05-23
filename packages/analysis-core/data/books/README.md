# Opening books

The canonical book for Clean Match Chess is **Lichess Masters Polyglot
(≥ 2400 Elo, depth 20 plies)** — see `manifest.json`.

## Status

`lichess-masters-2400-d20.bin` is **not yet bundled** with the
repository. The file is generated from the Lichess masters PGN corpus
via `polyglot-create` and pinned by SHA256 in `manifest.json`.

## Build instructions (deferred follow-up task)

```bash
# 1. Download the Lichess Masters PGN export (separate corpus task).
# 2. Filter to games with both players >= 2400 Elo.
# 3. Generate Polyglot book at depth 20:
polyglot-create -in masters-2400.pgn -out lichess-masters-2400-d20.bin -depth 20
# 4. Compute SHA256, update manifest.json's `sha256` field, set status to "bundled".
```

## Behaviour without the book

`OpeningBook(path)` raises `FileNotFoundError` if the binary is
missing. Pipeline callers in Phase 3 will catch this, log a warning,
and treat every ply as non-book (no opening discount applied). The
manifest will record `opening_book_sha256` as a sentinel
("0000...") and the report-engine will surface a "no opening discount
applied" disclaimer.
