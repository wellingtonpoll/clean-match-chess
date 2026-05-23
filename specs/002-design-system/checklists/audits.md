# Audit-Pipeline Requirements Quality Checklist: Forensic Analytics Design System

**Purpose**: Validate the *requirements writing* around the four-audit gate (palette / typography / motion / lexical) and the manifest provenance — completeness, clarity, consistency, measurability, and coverage. Unit-tests-for-English on the audit pipeline itself; this checklist does NOT verify any rendered artefact.

**Created**: 2026-05-23

**Feature**: [spec.md](../spec.md)

**Depth**: Standard · **Audience**: Reviewer (PR) · **Focus areas**: audit scope + invocation, failure semantics, cross-feature contracts (001-fairplay-analysis), reproducibility, override discipline

## Requirement Completeness

- [ ] CHK001 Are the four audit types (palette, typography, motion, lexical) each given a binding scope of which surfaces they cover (PDF, HTML, web, CLI text, JSON, templates)? [Completeness, Spec §FR-013, §FR-017]
- [ ] CHK002 Are requirements defined for *when* each audit runs (pre-render template scan, post-render artefact scan, CI gate, audit-replay) rather than only *what* it checks? [Completeness, Spec §FR-017]
- [ ] CHK003 Are requirements for the audit exit-code semantics (0 pass / 1 finding / 2 missing artefact / 3 internal bug) specified consistently across all four audits? [Consistency, Contracts §audit-*]
- [ ] CHK004 Are CI invocation rules documented — which audit marks block merge, which warn, which can be skipped on labelled PRs? [Completeness, Spec §FR-017]
- [ ] CHK005 Are requirements specified for audit *output* — what schema does an AuditReport JSON file follow, what is a finding's mandatory shape (severity, rule, location, expected, actual, message)? [Completeness, Contracts §audit-*]
- [ ] CHK006 Are requirements defined for audits running on partial artefacts (e.g., a report-engine emits HTML before PDF; audit runs on the intermediate)? [Gap, Coverage]
- [ ] CHK007 Are requirements defined for audits invoked outside CI — local-dev quickstart commands, IDE hooks, pre-commit? [Coverage, Quickstart §5-§6]
- [ ] CHK008 Are requirements specified for the override mechanism (exceptions list, expiry, reviewer) for motion, and is its absence intentional for palette/typography/lexical? [Gap, Contracts §audit-motion §Override discipline]
- [ ] CHK009 Are requirements defined for the per-language scan of the lexical audit on JSON output where forbidden-term keys could leak into structured data, not just human text? [Coverage, Contracts §audit-lexical]
- [ ] CHK010 Are requirements specified for *which* design-system version an audit re-run uses when an old artefact is being replayed (embedded in manifest vs locally installed)? [Completeness, Contracts §manifest-field]

## Requirement Clarity

- [ ] CHK011 Is "forbidden hue range" (palette audit) expressed with concrete HSL bounds and a saturation threshold (`hue ∈ [350°, 360°] ∪ [0°, 20°]` at `S > 30%`) rather than prose? [Clarity, Spec §FR-002, Contracts §audit-palette]
- [ ] CHK012 Is the palette Track-B per-pixel tolerance ("≤ 1% per-page anti-aliasing fringe") expressed as a precise denominator (per-page pixel count) and method (counting failed pixels, not failed regions)? [Clarity, Spec §SC-001, Contracts §audit-palette]
- [ ] CHK013 Is "headline metric" defined precisely enough for the typography audit to deterministically identify which DOM/PDF nodes must use `typography.metric`? [Clarity, Spec §FR-003, Contracts §audit-typography]
- [ ] CHK014 Is "the locked easing curve" expressed as a numeric `cubicBezier` value with rounding tolerance (e.g., 4 decimal places) so the motion audit knows when to fail? [Clarity, Spec §FR-005, Contracts §audit-motion]
- [ ] CHK015 Is the lexical-audit matching mode taxonomy (`word_boundary | substring`) defined with concrete regex equivalents and case-sensitivity rule? [Clarity, Contracts §audit-lexical]
- [ ] CHK016 Is "the design-system Delta-E threshold" (palette Track B) given a single value (5.0) and the colour space (Lab CIE76 vs CIEDE2000) made explicit? [Clarity, Contracts §audit-palette]
- [ ] CHK017 Is "audit performance budget" expressed with both a wall-clock target (s) and the reference machine spec, not just a number? [Clarity, Plan §Performance Goals, Contracts §audit-*]

## Requirement Consistency

- [ ] CHK018 Do the palette and motion audits use the same "forbidden literal" enforcement story (any literal value not derivable from `tokens.json` fails) so authors don't learn two different rules? [Consistency, Contracts §audit-palette §audit-motion]
- [ ] CHK019 Do the four audits emit a *uniformly shaped* `AuditReport` JSON, or does each have idiosyncratic fields? [Consistency, Contracts §audit-*]
- [ ] CHK020 Is the lexical audit's source-of-truth (`tests/fixtures/forbidden-terms/{en,pt}.txt`) identical to the path declared by feature 001's SC-008, including the per-row schema? [Consistency, Cross-feature 001 SC-008, Spec §FR-012]
- [ ] CHK021 Is the language set `{en, pt}` declared identically in this feature's spec, contracts, and feature 001's spec — no asymmetric subsets that would let one audit pass while another fails? [Consistency, Cross-feature 001]
- [ ] CHK022 Does the audit-replay tool honour the same exit-code table as the live audits, or do replays have softer semantics? [Consistency, Contracts §manifest-field]
- [ ] CHK023 Is the design-system version source (`packages/design-system/pyproject.toml`) referenced by exactly one path in the spec/contracts, with no parallel sources of truth? [Consistency, Contracts §manifest-field, Spec §FR-016]
- [ ] CHK024 Are the four audits' pytest marks (`audit_palette`, `audit_typography`, `audit_motion`, `audit_lexical`) referenced identically in every contract and the spec? [Consistency, Contracts §audit-*]

## Acceptance Criteria Quality

- [ ] CHK025 Can "100% of pixels drawn from the locked palette" (SC-001) be objectively decided given the stated 1% fringe tolerance, or is the wording self-contradictory (100% vs 99%)? [Measurability, Spec §SC-001]
- [ ] CHK026 Can "zero forbidden-term matches" (SC-002) be objectively measured for the JSON output, where strings may be nested under keys that themselves match a forbidden term? [Measurability, Spec §SC-002]
- [ ] CHK027 Can SC-004 ("transitions within 200–350 ms, locked curve, 0 ms when reduced-motion") be measured deterministically across browsers (Chromium / Firefox / WebKit)? [Measurability, Spec §SC-004]
- [ ] CHK028 Is SC-005 ("WCAG AA contrast") tied to a concrete table of audited token pairs rather than a global claim? [Measurability, Spec §FR-015, §SC-005]
- [ ] CHK029 Is SC-008 ("design_system_version present in manifest") measurable by an automated assertion, and is the assertion's location (which test file) declared? [Measurability, Spec §SC-008]
- [ ] CHK030 Are SC pass-thresholds (≥80% in usability, ≥95% opening-book agreement, etc.) backed by a defined measurement window and sample-size rule? [Measurability, Spec §SC-006]

## Scenario Coverage

- [ ] CHK031 Are requirements defined for the audit running against a *partial-success* report (feature 001 `status=partial`)? [Gap, Coverage]
- [ ] CHK032 Are requirements defined for the audit running against an empty / zero-finding template (no narrative segments to render)? [Gap, Coverage]
- [ ] CHK033 Are requirements specified for the *first* audit run after a token change but before the adapter is recompiled (stale committed CSS)? [Gap, Coverage, Contracts §token-file-schema §Compile targets]
- [ ] CHK034 Are requirements defined for replaying an audit when the embedded design-system version is no longer installable (deleted release)? [Gap, Coverage, Contracts §manifest-field]
- [ ] CHK035 Are requirements defined for partial multi-language coverage (lexical audit gets a forbidden-terms file for `en` but not `pt` after a localization regression)? [Gap, Coverage]
- [ ] CHK036 Are requirements defined for the audits running against artefacts produced *before* the manifest-field landed (backwards-compatibility scenario)? [Coverage, Contracts §manifest-field]

## Edge Case Coverage

- [ ] CHK037 Are requirements defined for the palette audit when an artefact embeds an image (PNG / SVG photograph) whose pixels are out-of-palette by design? [Edge Case, Spec §Edge Cases]
- [ ] CHK038 Are requirements specified for SVG charts that use anti-aliased gradients between two palette colours (every intermediate pixel is mathematically off-palette)? [Edge Case, Gap]
- [ ] CHK039 Are requirements defined for the lexical audit on PDF text extracted with ligature artefacts (`fi` → `ﬁ`) that may hide forbidden terms? [Edge Case, Gap, Contracts §audit-lexical]
- [ ] CHK040 Are requirements defined for forbidden terms that appear inside a code block or `code-inline` component, where the term may be a legitimate identifier (`is_cheater`, `fraud_score`)? [Edge Case, Conflict]
- [ ] CHK041 Are requirements defined for the motion audit on dynamic transitions triggered by JavaScript that bypasses CSS (Framer Motion direct-style mutation)? [Edge Case, Gap, Contracts §audit-motion]
- [ ] CHK042 Are requirements defined for very large artefacts (e.g., a 500-game report PDF) where the audit budget might be exceeded? [Edge Case, Spec §Plan §Performance Goals]
- [ ] CHK043 Are requirements defined for audits running on artefacts produced from a *future* design-system version (the consumer has an older package than the producer)? [Edge Case, Contracts §manifest-field §Backwards compatibility]

## Non-Functional Requirements

- [ ] CHK044 Are requirements defined for the audit pipeline's own observability — where does a contributor see *why* an audit failed (file path, location, expected vs actual)? [Gap, Spec §FR-017]
- [ ] CHK045 Are requirements specified for the audit's behaviour under flaky test conditions (Playwright timing jitter, font-loading races) — retry policy, max attempts, marking? [Gap, Contracts §audit-motion]
- [ ] CHK046 Are security requirements addressed for the audit pipeline — e.g., the lexical audit reading untrusted PDF text, the palette audit rasterising untrusted images? [Gap]
- [ ] CHK047 Is the rate at which the four audits run in CI bounded so that a typical PR completes in a documented time budget? [Clarity, Plan §Performance Goals]
- [ ] CHK048 Are versioning rules clear enough that adding a forbidden term is unambiguously a MINOR bump, removing one is MAJOR, and refining one is PATCH? [Clarity, Spec §FR-016]
- [ ] CHK049 Is the audit pipeline's failure mode (one finding fails the whole audit, or partial findings are reported and the worst severity decides) declared and consistent across the four audits? [Consistency, Contracts §audit-*]

## Dependencies & Assumptions

- [ ] CHK050 Is the dependency on `pdfminer.six` (lexical audit, typography audit) documented with a pinned minimum version and known-issue notes (ligature normalisation, glyph-to-text mapping)? [Dependency, Plan §Primary Dependencies]
- [ ] CHK051 Is the dependency on `colormath` (palette audit Delta-E) documented with the chosen colour difference formula (CIE76 vs CIEDE2000)? [Dependency, Plan §Primary Dependencies, Contracts §audit-palette]
- [ ] CHK052 Is the assumption "WeasyPrint emits structure tags reliably enough for the typography audit's role-based identification" validated, or is there a fallback path? [Assumption, Contracts §audit-typography]
- [ ] CHK053 Is the assumption "PDFs have no animations" validated against possible interactive PDF features (PDF/AX) that the report-engine might enable in the future? [Assumption, Contracts §audit-motion]
- [ ] CHK054 Is the cross-feature dependency on feature 001's `ReproducibilityManifest` documented as a contract (schema add-only, never schema-rename) so future feature-001 edits cannot silently break feature-002 replays? [Dependency, Contracts §manifest-field]
- [ ] CHK055 Is the assumption "every forbidden term has an `en` counterpart and a `pt` counterpart" validated by the loader on boot (mismatched lists → fail-fast)? [Assumption, Gap, Contracts §audit-lexical]

## Ambiguities & Conflicts

- [ ] CHK056 Does the spec resolve the apparent tension between "every audit blocks merge" (FR-017) and the explicit warn-not-fail backwards-compat case for missing `design_system_version` (Contracts §manifest-field)? [Conflict, Spec §FR-017, Contracts §manifest-field]
- [ ] CHK057 Is "the lexical audit MUST yield zero matches" (SC-002) reconciled with the legitimate need to mention forbidden terms in *documentation* like `docs/LEXICON.md` and the audit's own test fixtures? [Conflict, Spec §SC-002]
- [ ] CHK058 Is "intense yellow" (HIGH risk treatment, FR-007) the same value as `color.signal` from the token list, or a distinct token? [Ambiguity, Spec §FR-007, Data-model §RiskTreatment]
- [ ] CHK059 Does the motion audit treat the static-CSS check (always run, no skip) and the dynamic Playwright check (run only in Phase 3, opt-in) as the *same* audit with two modes, or as two distinct audits? Spec wording suggests one; contract treats them as two modes — clarify. [Ambiguity, Contracts §audit-motion]
- [ ] CHK060 Is the "audit-replay" workflow (Contracts §manifest-field) a CI-blocking gate or a developer convenience? Spec is silent; contract leaves it ambiguous. [Ambiguity, Contracts §manifest-field]

## Notes

- 60 items, IDs CHK001–CHK060.
- ≥80% include traceability references; remainder use `[Gap]` / `[Ambiguity]` / `[Conflict]` / `[Assumption]` markers per spec.
- Cross-feature anchors (CHK020, CHK021, CHK029, CHK054, CHK056) tie this audit pipeline back to feature 001-fairplay-analysis.
- This checklist tests the **audit requirements**, not the audit implementations. Failing items mean the spec/contracts need sharpening before `/speckit-implement`.
- Sister checklist: `ux.md` (design-system requirements quality, 55 items).
