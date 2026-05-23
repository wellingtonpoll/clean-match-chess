# PGN fixtures

Two fixture pools drive SC-001/SC-002/SC-004 acceptance tests.

## `known-clean/`

Real PGNs from public master games (high-rated humans, pre-engine era
or known-clean post-engine era). Used to assert the platform produces
LOW risk + few/no flagged segments on these inputs.

## `known-suspect/`

Two flavours:

1. **Full-engine games** (easy mode): engine-vs-engine games from
   the python-chess test suite or other public sources. These should
   trip every signal hard.

2. **Selective-assistance games** (hard mode, real threat model per
   spec SC-002 v1.0.0): human games with engine consultation at
   critical moments only. Synthetic in this initial seed —
   `corpus.json` documents the per-game provenance and any
   modification. Real-corpus selection is a follow-up curation task
   tracked in `tests/fixtures/sc-002/`.

## Format

Standard PGN. Each file MUST contain a single game. UTF-8. Newlines
LF.

## Schema

Each subdirectory MAY contain a `corpus.json` recording per-game
provenance (source URL, players, rating, modification notes, label).
