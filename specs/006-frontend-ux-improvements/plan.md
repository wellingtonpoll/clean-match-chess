# Implementation Plan: Frontend UX Improvements

**Branch**: `006-frontend-ux-improvements` | **Date**: 2026-05-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-frontend-ux-improvements/spec.md`

## Summary

Four frontend-only UX improvements landing as one cohesive change:

1. **US1 — Clickable player links**: Player usernames in `GameRow` cards become `<button>` elements that, on click, populate the search field with that username and trigger a new analysis on the current platform (no-op if username matches the current `activeUsername`).
2. **US2 — Expandable cards with layperson explanations**: `GameRow` gains a per-card expand/collapse state. Expanded state renders a "Análise detalhada" section with pt-BR explanations sourced from a new `lib/signalExplanations.ts` dictionary covering the 11 known signals + a fallback for unknown signals. Per Clarifications, the scope ends at "card expands, text is pt-BR, no unexplained jargon" — user-comprehension validation is out of scope.
3. **US3 — Sticky header**: Extract a `<Header>` component anchored at top of viewport via `position: fixed`. Carries the HorseLabs lockup (reduced scale) on left + search field + platform toggle on right. Mobile (< 480px) uses vertical stacking (brand row 1, search+toggle row 2). Hero section keeps its tagline but loses the search form (search moves exclusively to the header). Clicking HorseLabs = reset.
4. **US4 — Playwright cross-viewport tests**: New `apps/frontend/tests/e2e/` subtree with Playwright config + viewport matrix (375×667, 414×896, 1280×800, 1920×1080) + 5 bug-class detectors (overflow, hidden controls, truncation, hover-on-touch, scroll lock). Mocked `/api/analyze` SSE response so layout tests don't depend on the real backend. New CI job `frontend_e2e` path-filtered on `apps/frontend/**`.

**Technical approach**: Pure frontend refactor under `apps/frontend/`. No backend changes (FR-017, SC-007 enforce). Existing `page.tsx` is refactored to lift `runAnalysis` + state into a context (or simple prop drilling) so both Header search and player-link buttons can invoke it. New deps confined to dev: `@playwright/test`. CI infrastructure follows the pattern from feature 005's `fpr_gate` job (path filter + dedicated job + actions/cache for browser binaries).

**Side-fix: ESLint adoption (not user-visible)**: This feature adds `eslint` flat-config + plugins to `apps/frontend/` as infra cleanup for parity with the backend's `ruff` gate (constitution Principle I — "Linting MUST pass before merge"). It is NOT user-visible and has no FR/SC behind it. Documented here so the maintainer can descope it without affecting the user-facing scope of US1-US4. If descoped, remove tasks T003 and the `npm run lint` step from the `frontend_e2e` CI job — the rest of the feature is unaffected.

## Technical Context

**Language/Version**: TypeScript 5.8 + React 19 (existing stack, unchanged).

**Primary Dependencies**: Existing — `next@15.5.18`, `react@19.1.0`, `react-dom@19.1.0`, `tailwindcss@4.1.7`. **NEW (dev-only)** — `@playwright/test@^1.49` (per Playwright LTS as of 2026-05). No runtime deps added.

**Storage**: N/A — pure client-side SPA, state lives in React hooks. No persistence layer touched.

**Testing**:
- Existing: zero frontend tests (gap before this feature).
- New: Playwright E2E suite at `apps/frontend/tests/e2e/`. Runs against `npm run dev` (Next.js dev server). Mocks `/api/analyze` via Playwright route interception with a fixed SSE-event payload. Suite invocation: `npm run test:e2e` (script added to `apps/frontend/package.json`).

**Target Platform**: Modern evergreen browsers (Chromium, WebKit, Firefox). Mobile = Chromium with viewport emulation (Playwright's `devices['iPhone SE']` / `devices['iPhone 11 Pro Max']` for accuracy; supplemented by 1280×800 + 1920×1080 desktop sizes). The constitution defines Phase 3 web UI as Next.js — this feature is the first concrete delivery into that surface.

**Project Type**: Web SPA (Next.js App Router). Single workspace member `apps/frontend` already in `pyproject.toml` workspace list (only Python packages; Next.js app sits outside the uv workspace and uses its own `package.json` + `npm`).

**Performance Goals** (per constitution Principle IV):
- Playwright E2E suite: **≤ 5 min wall** on standard GitHub Actions runner with browser binaries cached; **≤ 8 min cold cache** (SC-004).
- UI interactions (clique-para-expandir, clique-para-pivotar): instantâneo-perceptual (< 100 ms perceived). No formal budget — qualitative gate.
- Card expansion doesn't trigger backend round-trip (state-only) → zero network cost.

**Constraints**:
- **FR-017 / SC-007**: No backend changes. The diff vs origin/main MUST stay within `apps/frontend/**`, `.github/workflows/ci.yml`, `CHANGELOG.md`, `specs/006-frontend-ux-improvements/**`.
- **Constitution Principle III (UX consistency)**: JSON envelope from `/api/analyze` is unchanged — frontend only consumes it. Player link click does NOT modify URL (SPA in-place state change) so back-button semantics deferred to a follow-up if needed (out of this scope).
- A11y: all interactive elements use semantic tags (`<button>` for in-app actions, `<a>` only for actual navigation). Focus visible.

**Scale/Scope**: Single page (`app/page.tsx`) + 3 existing components + 1-2 new components + 1 new dict module + Playwright test tree. Estimated < 1500 LOC added net.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|---|---|---|
| **I. Code Quality** | PASS | TypeScript strict mode (existing `tsconfig.json` config); ESLint recommended (the feature also adds it for parity with backend's ruff gate — see Phase 0 R3). No new transitive runtime deps; Playwright is dev-only. Public API surface (Next.js page + components) gets prop-typed interfaces, JSDoc on exported helpers. |
| **II. Testing Standards (NON-NEGOTIABLE)** | PASS | The Playwright suite IS the testing artifact for this phase. Per US4 acceptance, ≥ 5 bug classes detected; per FR-013, each detector has explicit assertion. Unit-test gap (no React Testing Library yet) acknowledged — Playwright covers the user-facing surface end-to-end; component-level RTL deferred to a follow-up if maintainer wants finer-grained unit tests. Constitution requires tests for "every signal computation, scoring aggregation, and report-rendering path" — this feature touches none of those; it touches a presentation-layer SPA. The Playwright suite satisfies the spirit of Principle II for this layer. |
| **III. UX Consistency** | PASS | JSON-first response semantics unchanged (Principle III applies to CLI today; the same rule extends to "API responses" when web UI lands per constitution text). Player link uses `<button>` not `<div onClick>`; expand/collapse uses `aria-expanded`; mobile stacking preserves both controls accessible (FR-011). |
| **IV. Performance Requirements** | PASS w/ documented budget | Playwright suite has explicit 5-min warm budget (SC-004 + FR-014). UI interactions are state-only (no backend) so qualitative "feels fast" is the gate. CI runtime regression > 10% blocks merge per constitution. |

**Constitution gate: PASS**. No violations; no Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/006-frontend-ux-improvements/
├── plan.md              # This file
├── research.md          # Phase 0: Playwright setup decisions, mock approach, lib placement, ESLint config
├── data-model.md        # Phase 1: SignalExplanation entity, ExpandableCardState, sticky header layout contract
├── quickstart.md        # Phase 1: maintainer recipes — run dev server, run E2E suite locally, add a new signal explanation
├── contracts/
│   ├── signal_explanations.contract.md   # Shape and semantics of the pt-BR explanation dictionary
│   └── playwright_e2e.contract.md         # Test invocation, viewport matrix, mock fixture format, CI integration
├── checklists/
│   └── requirements.md  # Spec quality checklist (already created during /speckit-specify)
└── tasks.md             # Phase 2 output (/speckit-tasks command — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
clean-match-chess/
├── apps/frontend/
│   ├── app/
│   │   ├── layout.tsx                     # NO CHANGE (or tiny — add Inter/Space Grotesk font preload if not present)
│   │   └── page.tsx                       # REFACTOR — extract <Header>, lift state, remove hero search form, add player-link click handlers
│   ├── components/
│   │   ├── Header.tsx                     # NEW — sticky brand + search + toggle, mobile stacking
│   │   ├── GameRow.tsx                    # REFACTOR — player names → <PlayerLink>; new expanded state; "Análise detalhada" section
│   │   ├── PlayerLink.tsx                 # NEW — semantic <button> wrapping a player name
│   │   ├── ExpandedAnalysis.tsx           # NEW — renders the pt-BR explanation per signal
│   │   ├── ProgressBar.tsx                # NO CHANGE
│   │   └── ExportButton.tsx               # NO CHANGE
│   ├── lib/
│   │   ├── signalExplanations.ts          # NEW — Record<SignalName, ExplanationCopy> + fallback + lookup helper
│   │   └── analyze.py                     # NO CHANGE (Python helper used by API route; out of scope)
│   ├── tests/
│   │   ├── e2e/
│   │   │   ├── viewports.ts               # NEW — central viewport matrix
│   │   │   ├── mock-stream.ts             # NEW — mocked SSE response factory + sample fixtures
│   │   │   ├── smoke.spec.ts              # NEW — hero loads, header renders in all viewports
│   │   │   ├── player-link.spec.ts        # NEW — US1 click → re-analyze flow
│   │   │   ├── expand-card.spec.ts        # NEW — US2 expand/collapse + content presence
│   │   │   ├── sticky-header.spec.ts      # NEW — US3 header visible after scroll, mobile stacking
│   │   │   ├── bug-detectors.spec.ts      # NEW — 5 detector classes (FR-013)
│   │   │   └── signal-explanations.spec.ts # NEW — SC-002 binary check (entries exist + pt-BR + no banned terms)
│   │   └── (unit tests for SignalExplanation lookup if added — optional)
│   ├── playwright.config.ts               # NEW — projects per viewport + base URL = dev server
│   ├── package.json                       # MODIFY — add `@playwright/test` to devDeps + `test:e2e` script
│   ├── tsconfig.json                      # NO CHANGE (or tiny tweak for tests/ include)
│   └── .eslintrc.json                     # NEW (or eslint.config.js — flat config) per Phase 0 R3
├── .github/workflows/
│   └── ci.yml                             # MODIFY — add `frontend_e2e` job with path filter + actions/cache for Playwright browsers
└── CHANGELOG.md                           # MODIFY — record feature 006 entry
```

**Structure Decision**: Keep all frontend work confined to `apps/frontend/`. New `tests/e2e/` subtree lives inside the frontend package (not the repo-root `tests/` tree where Python tests live) so it stays adjacent to the code it tests and `npm` tooling discovers it naturally. Playwright config sits at `apps/frontend/playwright.config.ts` so `cd apps/frontend && npm run test:e2e` is the invocation pattern.

## Complexity Tracking

No constitution violations. Table omitted.
