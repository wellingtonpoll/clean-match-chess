# UX & Design-System Requirements Quality Checklist: Forensic Analytics Design System

**Purpose**: Validate the *requirements writing* of the design-system spec — completeness, clarity, consistency, measurability, and coverage. Unit-tests-for-English on the design system itself; this checklist does NOT verify that any rendered surface matches the spec.

**Created**: 2026-05-23

**Feature**: [spec.md](../spec.md)

**Depth**: Standard · **Audience**: Reviewer (PR) · **Focus areas**: token quality, lexicon coverage, risk-treatment consistency, accessibility, cross-feature traceability

## Requirement Completeness

- [ ] CHK001 Are token sets defined for every visual dimension named in the spec — colour, typography, spacing, radius, shadow, motion, z-index? [Completeness, Spec §FR-001]
- [ ] CHK002 Are component-catalogue entries enumerated explicitly (Analytical Card, Risk Pill, Timeline, Heuristic Badge, Manifest Block, Code/Hex Inline) and is each entry's tokens-of-record list mandated? [Completeness, Spec §FR-009, §FR-010]
- [ ] CHK003 Are lexicon entries defined for every analytical noun used elsewhere in the platform (Behavioral Signal, Statistical Irregularity, Complexity Correlation, Tactical Precision Burst, Risk Window, Analytical Confidence)? [Completeness, Spec §FR-011]
- [ ] CHK004 Are forbidden-vocabulary categories ("accusation", "verdict", "slur") enumerated, and does each forbidden term carry a language + matching-mode tag? [Completeness, Spec §FR-012]
- [ ] CHK005 Are accessibility requirements declared for *each* component in the catalogue, not just globally? [Completeness, Spec §FR-010]
- [ ] CHK006 Are chart-series colour requirements specified, given that the main palette is intentionally narrow? [Gap, Spec §Edge Cases]
- [ ] CHK007 Are state requirements (hover, focus, active, disabled) defined for every interactive component in the catalogue? [Gap, Spec §FR-009]
- [ ] CHK008 Are loading / empty / partial-result state requirements defined for the Analytical Card and Timeline components? [Gap, Spec §FR-009]
- [ ] CHK009 Are localisation requirements declared for every user-facing string (not just lexicon entries) across both supported languages? [Coverage, Spec §Edge Cases]

## Requirement Clarity

- [ ] CHK010 Is "intense yellow on dark contrast" for the HIGH risk treatment quantified with the exact tokens used for fill, foreground, and border? [Clarity, Spec §FR-007]
- [ ] CHK011 Is the "amber" used for MEDIUM defined with a concrete hex/token value, distinct from Signal Yellow and from any red? [Clarity, Spec §FR-007]
- [ ] CHK012 Is "premium / soft" for the radius scale converted into a measurable rule (default radius value, when to use which)? [Clarity, Spec §FR-006]
- [ ] CHK013 Is the metrics typography rule expressed as exact tokens (size, weight, letter-spacing) rather than a range that lets contributors pick? [Clarity, Spec §FR-003]
- [ ] CHK014 Is the motion grammar phrased as a *single* enforceable easing curve and a *bounded* duration range with explicit override procedure? [Clarity, Spec §FR-005]
- [ ] CHK015 Is "the forbidden hue range" expressed in a way an automated audit can implement (specific HSL/Lab/Delta-E bounds) rather than as prose? [Ambiguity, Spec §FR-002, §SC-001]
- [ ] CHK016 Is "no off-system spacing" defined with the exact tolerance for sub-pixel rendering or anti-aliasing fringe pixels? [Clarity, Spec §FR-004, §SC-001]
- [ ] CHK017 Is "headline metric" defined precisely enough that a reviewer can decide which numbers in a report must use the metrics typography? [Ambiguity, Spec §FR-003]

## Requirement Consistency

- [ ] CHK018 Do the Risk Treatment definitions in FR-007/FR-008 align bit-for-bit with the risk-level thresholds locked by feature 001-fairplay-analysis (low<0.35, medium [0.35,0.70), high≥0.70)? [Consistency, Spec §FR-007, Cross-feature 001]
- [ ] CHK019 Is the forbidden-terms file path (`tests/fixtures/forbidden-terms/{en,pt}.txt`) the same path declared by feature 001-fairplay-analysis, and is the per-entry schema identical (category + matching mode)? [Consistency, Spec §FR-012, Cross-feature 001]
- [ ] CHK020 Are the supported languages (en, pt) declared identically here and in feature 001 so the audit isn't language-asymmetric? [Consistency, Spec §Assumptions, Cross-feature 001]
- [ ] CHK021 Do the "no red, anywhere" rule (FR-002, FR-007, Assumptions) and the colour-token list have zero conflicting entries? [Consistency, Spec §FR-002, §FR-007]
- [ ] CHK022 Are dark-mode-only requirements consistent across FR-001…FR-017 and the Assumptions section (no FR implicitly requires light-mode)? [Consistency, Spec §Assumptions]
- [ ] CHK023 Is the design-system version embedded in the manifest (FR-016) consistent with how feature 001's `ReproducibilityManifest` declares versioned dependencies? [Consistency, Spec §FR-016, Cross-feature 001 FR-015]

## Acceptance Criteria Quality

- [ ] CHK024 Can "100% of pixels … drawn from the locked palette" (SC-001) be objectively measured given the stated 1% anti-aliasing tolerance? [Measurability, Spec §SC-001]
- [ ] CHK025 Is the SC-006 usability target ("≥80% describe as 'analytical' or 'forensic'") backed by a defined script, panel selection rule, and pass/fail boundary? [Measurability, Spec §SC-006]
- [ ] CHK026 Are the contrast targets (≥3:1 non-text, ≥4.5:1 text) tied to a concrete table of which token pairs MUST pass, rather than a global claim? [Measurability, Spec §FR-015, §SC-005]
- [ ] CHK027 Is the motion-bound SC ("200–350 ms, locked curve, 0 ms when reduced-motion") tied to a deterministic measurement method (devtools timeline / instrumentation)? [Measurability, Spec §SC-004]
- [ ] CHK028 Is SC-007 ("contributor first-commit passes audits") tied to a sample-size threshold and a measurement window, or is "≥3 events" left open-ended in time? [Measurability, Spec §SC-007]
- [ ] CHK029 Is SC-008 ("design_system_version present in manifest") testable via an automated assertion in CI rather than manual inspection? [Measurability, Spec §SC-008]

## Scenario Coverage

- [ ] CHK030 Is User Story 1's "report renders in the forensic brand" coverage extended to the bundle export's intermediate HTML (which is byte-stable per feature 001) and not just the PDF? [Coverage, Spec §US1, Cross-feature 001]
- [ ] CHK031 Are requirements defined for the *partial-success* report case (e.g., feature 001 partial AccountProfile, status=partial)? [Gap, Coverage]
- [ ] CHK032 Are requirements defined for error-state web surfaces (502, 500, "Stockfish unavailable" upstream message)? [Gap, Spec §US2]
- [ ] CHK033 Are requirements defined for the contributor-authoring scenario when the design-system documentation itself is updated mid-PR? [Gap, Spec §US3]
- [ ] CHK034 Are requirements defined for the case where a forbidden-terms entry is added during a release window — must existing reports be regenerated or just future ones? [Gap, Coverage]

## Edge Case Coverage

- [ ] CHK035 Is the behaviour under `prefers-reduced-motion` defined identically for web and PDF surfaces, including the case where the PDF can't honour user OS settings? [Edge Case, Spec §Edge Cases, §FR-014]
- [ ] CHK036 Are requirements specified for very large numeric metrics (e.g., 10-digit run counts) that may overflow the metrics typography slot? [Edge Case, Gap]
- [ ] CHK037 Are requirements specified for users on monochrome displays / colourblind users, given that the design encodes risk entirely via yellow intensity? [Edge Case, Gap, Spec §FR-007]
- [ ] CHK038 Are requirements defined for the WeasyPrint CSS subset constraint — explicitly listing the CSS features the design system MUST NOT rely on? [Edge Case, Spec §Edge Cases]
- [ ] CHK039 Are requirements defined for SVG rendering parity between matplotlib-produced charts (feature 001) and Apache ECharts (Phase 3)? [Edge Case, Gap]
- [ ] CHK040 Are requirements defined for printing to physical paper (PDF → printer), where Obsidian Black backgrounds become ink-heavy and unusable? [Edge Case, Gap]

## Non-Functional Requirements

- [ ] CHK041 Are performance requirements defined for the design-system audits themselves (palette/typography/motion/lexical) so CI does not become a chokepoint? [Gap, Spec §FR-017]
- [ ] CHK042 Are observability requirements defined for design-system audit failures (where do reviewers see them, what level of detail)? [Gap, Spec §FR-017]
- [ ] CHK043 Are security requirements considered — e.g., the design system MUST NOT include third-party fonts/icons that exfiltrate request data? [Gap, Spec §Assumptions]
- [ ] CHK044 Are versioning rules (MAJOR/MINOR/PATCH) clear enough that a reviewer can categorise a given change without ambiguity? [Clarity, Spec §FR-016]
- [ ] CHK045 Are backwards-compatibility requirements defined for older reports — does an old report's `design_system_version` stay valid after a MAJOR bump? [Gap, Spec §FR-016]

## Dependencies & Assumptions

- [ ] CHK046 Is the dependency on feature 001-fairplay-analysis (forbidden-terms file path, language set, manifest schema) explicitly listed and traceable? [Dependency, Spec §FR-012, §Assumptions]
- [ ] CHK047 Is the assumption "Inter is licensable for embedded PDF use" validated, since WeasyPrint embeds fonts into the PDF? [Assumption, Spec §Assumptions]
- [ ] CHK048 Is the assumption "Manrope is a true drop-in fallback for Inter" validated against the metrics typography spec (letter-spacing −0.03em behaves identically)? [Assumption, Spec §Assumptions]
- [ ] CHK049 Is the deferred light-mode decision explicitly out-of-scope in every FR, or does any FR implicitly assume both themes? [Assumption, Spec §Assumptions]
- [ ] CHK050 Are the Phase-3 stack expectations (Tailwind / shadcn / ECharts / Framer Motion / Lucide) confined to Assumptions and never load-bearing on FRs/SCs? [Assumption, Spec §Assumptions]

## Ambiguities & Conflicts

- [ ] CHK051 Does the spec explicitly resolve the apparent tension between "premium / soft" radius prose (FR-006) and the strict 20–28 px range — which value is the *default*? [Ambiguity, Spec §FR-006]
- [ ] CHK052 Does the spec resolve potential conflict between FR-005 (single easing curve) and motion needs that genuinely call for a different curve (e.g., bounce on success, ease-in on disappear)? [Conflict, Spec §FR-005]
- [ ] CHK053 Is "intense yellow" in HIGH risk treatment distinguishable from "Signal Yellow" used for CTAs — same hex or different? [Ambiguity, Spec §FR-007, §Palette]
- [ ] CHK054 Does the spec disambiguate "headline metric" from "ordinary metric" so contributors know when metrics typography is required vs optional? [Ambiguity, Spec §FR-003]
- [ ] CHK055 Is a requirement & acceptance-criteria ID scheme established (FR-/SC- present, but no CHK→FR back-traceability mandated)? [Traceability]

## Notes

- 55 items. ≥80% include traceability references; remainder use `[Gap]` / `[Ambiguity]` / `[Conflict]` / `[Assumption]` markers per spec.
- Cross-feature consistency items (CHK018-CHK020, CHK023, CHK030, CHK046) anchor this design system to `001-fairplay-analysis`.
- This checklist tests the **requirements**, not the rendered UI. A failing item means the spec needs a sharpening edit before `/speckit-plan`, not that some code is broken.
- Items marked incomplete require spec updates before `/speckit-plan`.
