# analysis-core bundled data

## opening_book.bin

Synthetic minimal Polyglot opening book generated for feature 004 Phase 1.

Contents: mainline first 12 plies of 8 common openings (Italian, Ruy Lopez, Sicilian Najdorf, Queen's Gambit Declined, French, King's Indian, Caro-Kann, English).

- Format: Polyglot binary (16-byte entries: u64 zobrist + u16 move + u16 weight + u32 learn, sorted ascending by key).
- Entries: 81
- Size: 1296 bytes (well under 5 MB cap)
- sha256: `9e808a4e60ac6666036198327dcdef6c2411f72169f74794bf628610b2aab6c5`

Generator script: `/tmp/gen_book.py` (one-shot, reproducible — uses hardcoded mainline PGN lines + `chess.polyglot.zobrist_hash`). Maintainer can rebuild by re-running with the same opening lines.

For Phase 2+ a real GM-quality book (e.g., `gm2600.bin` or the Lichess masters polyglot mentioned in `books/README.md`) is the target. The synthetic stub here unblocks Phase 1 implementation and tests without external download dependencies.
