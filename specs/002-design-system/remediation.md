# Remediation Specification — Zero-Metrics Pass

**Feature**: `002-design-system` · **Date**: 2026-05-23

**Source**: Post-HIGH-remediation `/speckit-analyze` run. Goal: zero
MEDIUM + zero LOW findings.

**Status**: PROPOSED — no files have been edited yet. Approving this
document means each diff below MAY be applied verbatim, in order.

**Constraints honoured** (per user preference, same as HIGH pass):

- Minimal spec-surface changes.
- Tighten contracts; do not expand scope.
- Preserve phased-delivery strategy.
- No new architectural layers, no new modules.

---

## Inventory of remaining findings

| ID  | Severity | Category      | Target                                                    |
|-----|----------|---------------|-----------------------------------------------------------|
| I2  | MEDIUM   | Inconsistency | `spec.md` FR-013 (scope overcommit on "web pages")        |
| I3  | MEDIUM   | Inconsistency | `spec.md` FR-001 (format wording permissive)              |
| I4  | MEDIUM   | Inconsistency | `spec.md` FR-017 vs `contracts/manifest-field.md`         |
| A3  | MEDIUM   | Ambiguity     | `spec.md` Edge Cases (WeasyPrint subset not enumerated)   |
| A4  | MEDIUM   | Ambiguity     | `spec.md` FR-006 (default radius undeclared)              |
| C3  | MEDIUM   | Coverage Gap  | `spec.md` SC-007 (onboarding measurement infra)           |
| C4  | MEDIUM   | Coverage Gap  | `spec.md` FR-014 + `tasks.md` (PDF reduced-motion case)   |
| L1  | LOW      | Inconsistency | `spec.md` FR-014 vs `tasks.md` T067 env-gate              |
| L2  | LOW      | Inconsistency | Saturation unit implicit across three files               |
| L3  | LOW      | Stylistic     | `tasks.md` T094 wording ("feature 001's render_html.py")  |
| L4  | LOW      | Stylistic     | `data-model.md` §AuditFinding rule examples missing       |

Total: 10 findings (7 MEDIUM + 4 LOW — L4 elevated to its own line for
clarity; it was footnoted in the prior analysis report).

---

## Edit 1 — Finding I2 (FR-013 scope)

**File**: `specs/002-design-system/spec.md`

**Current text**:

```text
- **FR-013**: Every user-facing surface (report PDF, report HTML, web
  pages) MUST pass the lexical audit (zero matches against the forbidden
  list) before release.
```

**Proposed text**:

```text
- **FR-013**: Every user-facing surface delivered by this feature
  (report PDF, report HTML, synthetic web fixture from US2) MUST pass
  the lexical audit (zero matches against the forbidden list) before
  release. Real Phase-3 web surfaces (dashboard, audit detail, account
  profile) inherit this requirement as part of the follow-up "Phase 3
  web surfaces" feature; the audit pipeline is the same, only the
  consumed artefacts differ.
```

**Rationale**: Aligns FR-013 with US2's resolved scope (synthetic
fixture only). Real web pages remain governed by the same FR text in a
follow-up feature without weakening any guarantee.

---

## Edit 2 — Finding I3 (FR-001 format)

**File**: `specs/002-design-system/spec.md`

**Current text**:

```text
- **FR-001**: The system MUST publish a single source-of-truth design-token
  artefact in a machine-readable format (e.g., JSON / W3C Design Tokens
  Community Group format) covering: colour, typography, spacing, radius,
  shadow, motion (duration + easing), and z-index.
```

**Proposed text**:

```text
- **FR-001**: The system MUST publish a single source-of-truth design-token
  artefact in **W3C Design Tokens Community Group (DTCG) JSON**, covering:
  colour, typography, spacing, radius, shadow, motion (duration + easing),
  and z-index. The format is binding; alternative serialisations
  (YAML, TOML, vendor JSON) are rejected.
```

**Rationale**: Plan, research §1, and `contracts/token-file-schema.md`
all lock DTCG JSON. Spec wording catches up.

---

## Edit 3 — Finding I4 (FR-017 vs manifest-field warn-mode)

**File**: `specs/002-design-system/spec.md`

**Current text**:

```text
- **FR-017**: A CI gate MUST run on every change that touches a user-
  facing surface and MUST execute, at minimum: palette audit, typography
  audit, motion audit, lexical audit. Any failure blocks merge.
```

**Proposed text**:

```text
- **FR-017**: A CI gate MUST run on every change that touches a user-
  facing surface and MUST execute, at minimum: palette audit, typography
  audit, motion audit, lexical audit. Any audit **finding of severity
  `block`** fails the gate and blocks merge. Findings of severity `warn`
  (e.g., the documented backwards-compat case in
  `contracts/manifest-field.md` for legacy manifests missing
  `design_system_version`) are surfaced in the CI summary but do not
  block merge. The set of warn-only rules is closed and enumerated in
  the audit contracts; no new warn-only rule may be added without a
  spec amendment.
```

**Rationale**: Resolves the contradiction. Carves out the *one*
documented warn-mode case explicitly and pins the warn list to the
contracts so it cannot grow silently.

---

## Edit 4 — Finding A3 (WeasyPrint subset enumeration)

**File**: `specs/002-design-system/spec.md`

**Current text** (Edge Cases bullet):

```text
- **Print / PDF**: WeasyPrint's CSS subset must be respected — the design
  system MUST be expressible without features WeasyPrint cannot render.
```

**Proposed text**:

```text
- **Print / PDF**: The design system MUST be expressible inside
  WeasyPrint's documented CSS subset for WeasyPrint 60+. The following
  features are explicitly disallowed in any token output or template
  consumed by the PDF render path:
  - CSS Grid
  - Container queries
  - `:has()` selector
  - Logical-property variants beyond `margin-*` / `padding-*`
    (`inset-block-*` etc.)
  - Subgrid
  Flexbox and CSS custom properties (`--*`) ARE permitted. Layout
  beyond flex relies on tables. Adapter compilers MUST reject token
  output that introduces any disallowed feature.
```

**Rationale**: Moves the binding list out of research §3 and into the
spec body where reviewers must consult it.

---

## Edit 5 — Finding A4 (FR-006 default radius)

**File**: `specs/002-design-system/spec.md`

**Current text**:

```text
- **FR-006**: The radius token set MUST define a "large" radius in the
  `20–28 px` range as the default for cards and analytical surfaces.
```

**Proposed text**:

```text
- **FR-006**: The radius token set MUST define four named values:
  `sm` (8 px), `md` (16 px), `lg` (24 px, **default for analytical
  surfaces**), `xl` (28 px). The `lg`/`xl` pair covers the locked
  20–28 px range for "premium / soft" treatment; `lg` is the default
  unless a component's catalogue entry explicitly requires `xl`.
```

**Rationale**: Locks the default. Removes the "premium / soft" prose
ambiguity. Matches `contracts/token-file-schema.md` values verbatim.

---

## Edit 6 — Finding C3 (SC-007 onboarding measurement)

**Files**:

1. `specs/002-design-system/tasks.md` — append one task.

**Proposed task** (insert in Phase 7, after T096):

```text
- [ ] T097 [P] Author `packages/design-system/docs/SC007_ONBOARDING_LOG.md`
  defining: "onboarding event" (a PR labelled `onboarding-event` whose
  author has fewer than 3 prior commits to `packages/design-system/`
  or `packages/report-engine/`); pass criterion (all four audits clean
  on first commit, before any maintainer push); tally template
  (`SC007_RESULTS.md` with rows of date, contributor, PR URL,
  pass/fail). Add a CI step in `.github/workflows/ci.yml` that, on
  labelled PRs, appends a row to `SC007_RESULTS.md` and re-evaluates
  the rolling ≥3-event passing-rate. The doc itself MUST pass the
  lexical audit (en + pt where applicable).
```

**Rationale**: Mirrors the T096 / SC-006 pattern. Tightens the measurement
contract without introducing new tooling.

---

## Edit 7 — Finding C4 (PDF reduced-motion explicit case)

**Files**:

1. `specs/002-design-system/tasks.md` — append one task.

**Proposed task** (insert in Phase 7, after T097):

```text
- [ ] T098 [P] [US1] Write unit test
  `packages/design-system/tests/unit/test_pdf_reduced_motion.py`
  asserting the generated `adapters/weasyprint/tokens.css` contains
  zero `transition` and zero `animation` CSS declarations. This
  enforces FR-014 trivially for the PDF surface (which has no motion)
  and prevents future drift from accidentally adding animated CSS to
  the PDF adapter.
```

**Rationale**: One-line invariant test makes the trivially-true PDF case
explicit. No production code change.

---

## Edit 8 — Finding L1 (T067 env-gate vs FR-014 MUST)

**File**: `specs/002-design-system/spec.md`

**Current text** (Assumptions section, between existing bullets):

```text
- **Stack alignment**: …
- **Source-of-truth location**: …
```

**Proposed insertion** (new bullet, place before "Stack alignment"):

```text
- **Motion-audit CI gating**: the dynamic motion audit (Playwright,
  T067) is environment-gated by `CLEANMATCH_WEB_AUDIT=1` in MVP because
  there is no real web surface to audit yet — the synthetic web fixture
  exercises the harness, but the gate prevents Playwright from running
  on every PR in CI. FR-014's MUST clause is satisfied today by the
  static-CSS audit (T039) on the WeasyPrint adapter and by the
  zero-motion unit test added under finding C4 (T098). When the Phase-3
  web surfaces feature lands, the env-gate is removed and the dynamic
  audit becomes default-on.
```

**Rationale**: Documents the gate's existence and explicitly preserves
FR-014's binding character via the static + zero-motion tests.

---

## Edit 9 — Finding L2 (saturation unit)

**File** A: `specs/002-design-system/spec.md`

**Current text** (FR-002):

```text
- **FR-002**: The colour token set MUST include the locked palette
  (Obsidian Black, Soft White, Signal Yellow, Neutral Gray, Dark Surface,
  Border Gray) and MUST forbid red hues (no token in the red hue range
  350°–20° at >30% saturation).
```

**Proposed text**:

```text
- **FR-002**: The colour token set MUST include the locked palette
  (Obsidian Black, Soft White, Signal Yellow, Neutral Gray, Dark Surface,
  Border Gray) and MUST forbid red hues. A colour is "red" iff, in HSL,
  its hue falls in `[350°, 360°] ∪ [0°, 20°]` AND its saturation exceeds
  **30 percent** (HSL saturation expressed in the 0–100 % range).
```

**File** B: `specs/002-design-system/research.md` — replace the bullet
that mentions saturation > 30% with the same explicit "0–100 %" wording.

**File** C: `specs/002-design-system/contracts/audit-palette.md` — replace
`S > 30%` with `HSL saturation > 30% (0–100 % range)`.

**Rationale**: Removes any implementer ambiguity between 0–1 and 0–100
saturation.

---

## Edit 10 — Finding L3 (T094 wording)

**File**: `specs/002-design-system/tasks.md`

**Current text** (T094):

```text
- [ ] T094 [US1] Implement Track C in `packages/design-system/src/design_system/audits/palette.py::audit_risk_indicators` per `contracts/audit-palette.md` Track-C section (turns T093 green); update feature 001's `packages/report-engine/src/report_engine/render_html.py` and PDF risk-pill rendering (T056) to emit the role marker and to consume `RiskTreatment` constants exclusively
```

**Proposed text**:

```text
- [ ] T094 [US1] Implement Track C in `packages/design-system/src/design_system/audits/palette.py::audit_risk_indicators` per `contracts/audit-palette.md` Track-C section (turns T093 green); extend the risk-pill rendering introduced by T056 in `packages/report-engine/src/report_engine/render_html.py` and the PDF structure-tree producer in `packages/report-engine/src/report_engine/render_pdf.py` to emit the role marker (`data-role="risk-pill"` / PDF role `Risk-Pill`) and to consume `RiskTreatment` constants exclusively
```

**Rationale**: Removes the misleading "feature 001's" attribution
(T056 is feature 002's task; the file is shared) and names the PDF
producer file explicitly.

---

## Edit 11 — Finding L4 (`AuditFinding.rule` examples)

**File**: `specs/002-design-system/data-model.md`

**Current text** (§9 `AuditFinding`):

```text
| `rule`        | `str`           | e.g., `forbidden_hue`, `off_spacing`, `forbidden_term`, `motion_too_fast`. |
```

**Proposed text**:

```text
| `rule`        | `str`           | e.g., `forbidden_hue`, `off_spacing`, `forbidden_term`, `motion_too_fast`, `missing_metric_role`, `missing_risk_role`, `risk_treatment_non_canonical`, `wrong_metric_typography`, `wrong_role_typography`, `motion_out_of_range`, `motion_wrong_easing`, `motion_ignored_reduced_motion`, `manifest_missing_design_system_version` (warn-only), `unknown_color_literal`, `off_palette_pixels`. |
```

**Rationale**: Pure documentation completeness; aligns the example list
with every rule named across the four audit contracts.

---

## Application order

If approved, apply in the listed order (E1 → E11). Each edit is
independent of the others except E6 (T097) and E7 (T098), both of
which append to Phase 7 and MUST be inserted in order (T097 before
T098) to keep IDs sequential.

## Post-application expected metrics

| Metric                                | Before | After  |
|---------------------------------------|--------|--------|
| HIGH issues                           | 0      | 0      |
| MEDIUM issues                         | 7      | **0**  |
| LOW issues                            | 3 + L4 | **0**  |
| Coverage % (requirements with ≥1 task)| 100%   | 100%   |
| Partial-coverage requirements         | 4      | **0**  |
| Total tasks                           | 96     | **98** |

## Out of scope for this remediation

- No constitution amendment.
- No new audit module (E6 documents a measurement protocol;
  E7 is a one-line test, E11 is doc).
- No new feature branch.
- No CLI surface changes.

## Sign-off line

Approve all 11 edits with `apply all`. Approve a subset with
`apply E1 E3 E6 …`. Reject with `reject` and propose alternatives.
Per prior-pass convention, I will NOT edit files until explicit
approval is given.
