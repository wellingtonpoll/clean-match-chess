"""Feature 005 — labeled-corpus false-positive-rate gate utilities and tests.

Modules:
- ``provenance``: load and validate ``*.provenance.json`` sidecars for corpus fixtures.
- ``cache``: per-fixture engine-analysis cache keyed by PGN sha256.
- ``gate``: orchestrator that runs the audit pipeline over a corpus and computes FPR/TPR.

Public test target ``test_fpr_gate.py`` invokes ``gate.run_gate`` against
``tests/fixtures/corpora/`` and asserts the thresholds in
``specs/005-scoring-v2-phase2/contracts/fpr_gate.contract.md``.
"""
