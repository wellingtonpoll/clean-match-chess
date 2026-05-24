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

## Phase 2 — real gm2600.bin (TARGET)

This file will be populated when feature 005 (Scoring v2 Phase 2) task T011 lands.

When updating, replace this stanza with:

- **Source URL**: `<URL the maintainer downloaded from>` (record exact URL)
- **Retrieved at**: `<ISO 8601 UTC timestamp>`
- **sha256**: `<64-char hex from sha256sum gm2600.bin>`
- **Size**: `<bytes>` (expected ≥ 1 MB)
- **License/provenance note**: 1 line stating the upstream's redistribution terms.

Phase 1's stub remains the source of truth until the real artifact lands; once it does, the stub's sha256 above is invalidated and the new sha256 propagates through `manifest.opening_book_sha256` for every audit.
