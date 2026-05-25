---
description: "Task list for feature 006 — Frontend UX Improvements"
---

# Tasks: Frontend UX Improvements

**Input**: Design documents from `/specs/006-frontend-ux-improvements/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — Playwright E2E suite is the testing artifact for this feature (constitution Principle II). Each User Story phase ships tests + implementation; signal-explanations dictionary has a dedicated binary test (SC-002).

**Organization**: Tasks grouped by user story. All work confined to `apps/frontend/` + `.github/workflows/ci.yml` + `CHANGELOG.md` + this feature's spec dir (FR-017 / SC-007).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Includes exact file paths

## Path Conventions

Repo-relative. All frontend paths sit under `apps/frontend/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add Playwright dev dep, lint/type config, ensure dev server runs.

- [X] T001 Modify `apps/frontend/package.json`: add `@playwright/test@^1.49` to `devDependencies`; add scripts `"test:e2e": "playwright test"` and `"test:e2e:ui": "playwright test --ui"` and `"lint": "next lint"`. Run `cd apps/frontend && npm install` from repo root.
- [X] T002 [P] Run `cd apps/frontend && npx playwright install chromium webkit --with-deps` once locally. (CI invokes this in the `frontend_e2e` job; this task is for the maintainer's local environment.)
- [X] T003 [P] Create `apps/frontend/eslint.config.js` (flat config) per research.md R3. Include `@typescript-eslint`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, and Next.js recommended preset. Add corresponding devDependencies to `apps/frontend/package.json`.
- [X] T004 Modify `apps/frontend/package.json`: ensure `"type-check": "tsc --noEmit"` script exists (already present per inspection); verify `tsconfig.json` includes `tests/e2e/**/*.ts`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Lift `runAnalysis` + state into a context so Header (US3) and PlayerLink (US1) can share the same actions. BLOCKS US1 + US3.

**⚠️ CRITICAL**: No user story implementation can begin until T005-T007 land.

- [X] T005 Create `apps/frontend/lib/AnalysisContext.tsx` per data-model.md §6: exports `AnalysisContext`, `AnalysisProvider`, and `useAnalysisContext()`. Provider lifts state (`username`, `platform`, `sessions`, `isAnalyzing`, `activeUsername`, `abortRef`) from `page.tsx` and exposes `runAnalysis(offset, opts?)` + `reset()`. `runAnalysis` accepts an optional `{ newUsername }` that overrides the current username for this invocation AND syncs back to the context state.
- [X] T006 Modify `apps/frontend/app/layout.tsx`: wrap `{children}` with `<AnalysisProvider>`. Verify the rest of the layout remains unchanged.
- [X] T007 Refactor `apps/frontend/app/page.tsx`: remove local `useState` for state now in the context; consume `useAnalysisContext()`; keep page-level layout structure. This refactor is intentionally INCOMPLETE w.r.t. the new Header (US3) — the hero search form remains in place until US3 lands. Test: existing manual smoke (start dev server, run an analysis) still works.

**Checkpoint**: Context infrastructure ready. US1, US2, US3 implementations can begin.

---

## Phase 3: User Story 1 - Clickable Player Links (Priority: P1)

**Goal**: Player names in game cards become clickable; clicking triggers re-analysis for that player on the current platform.

**Independent Test**: Mock a game with `White: alice, Black: bob`, render the page, click "bob" — `activeUsername` becomes "bob", sessions reset, a new analysis starts for "bob".

### Tests for User Story 1

- [X] T008 [P] [US1] Write `apps/frontend/tests/e2e/fixtures/mixed-5-games.txt` per data-model.md §7 and research.md R2: 5 SSE events covering low + medium + high risk games with diverse `dominantSignals`, ending with `data: {"done": true}`.
- [X] T009 [P] [US1, **SHARED INFRA** — also blocks T014/T020/T027 in US2/US3/US4] Write `apps/frontend/tests/e2e/mock-stream.ts` per contracts/playwright_e2e.contract.md: exports `mockStream(page: Page, scenario: string)` that reads the fixture file and registers `page.route('**/api/analyze*', ...)`. Although placed under US1's phase, this helper is consumed by every US's test file — execute it first in any US1 sub-batch.
- [X] T010 [US1, depends on T008+T009] Write `apps/frontend/tests/e2e/player-link.spec.ts` covering US1 AS1, AS2, AS3, AS4: (a) click opponent name → new analysis fires with that username, (b) click during in-flight analysis → abort + restart, (c) click on current subject → no-op, (d) platform persists across re-analyze.

### Implementation for User Story 1

- [X] T011 [P] [US1] Create `apps/frontend/components/PlayerLink.tsx` per data-model.md §2. Renders `<span>` (subject) or `<button type="button">` (opponent) with `aria-label="Analisar partidas de {username}"`. Click handler calls `useAnalysisContext().runAnalysis(0, { newUsername: username })`.
- [X] T012 [US1, depends on T011] Modify `apps/frontend/components/GameRow.tsx`: replace inline `parseResult(headers)` rendering with separate `<PlayerLink username={white} isSubject={white === activeUsername} />` + " vs " + `<PlayerLink username={black} isSubject={black === activeUsername} />` + " — " + result. Read `activeUsername` from `useAnalysisContext()`.

**Checkpoint**: US1 functional + tested. Click a player name → re-analyze.

---

## Phase 4: User Story 2 - Expandable Cards with Layperson Explanations (Priority: P1)

**Goal**: Cards expand on click to show pt-BR explanations of each `dominant_signal`.

**Independent Test**: Mock a high-risk game with 2 dominant signals, render, click the card — expanded section appears with 2 explanation blocks in pt-BR. Click again — collapses.

### Tests for User Story 2

- [X] T013 [P] [US2] Write `apps/frontend/tests/e2e/fixtures/suspect-1-game.txt`: single game with `score=0.87`, `risk_level="high"`, 3 dominant_signals (worst-case layout for expanded section).
- [X] T014 [P] [US2] Write `apps/frontend/tests/e2e/expand-card.spec.ts` covering US2 AS1, AS2, AS3, AS4, AS5: expand, collapse, no-expand on `pending`/`error`, independent state per card, fallback for unknown signals.
- [X] T015 [P] [US2] Write `apps/frontend/tests/e2e/signal-explanations.spec.ts` per contracts/signal_explanations.contract.md §"Test surface": (a) every `SignalName` key has a non-empty entry, (b) no entry's `body` matches any pattern in `JARGON_BLACKLIST`, (c) `explainSignal("unknown")` returns `FALLBACK_EXPLANATION`. This test satisfies the reworked SC-002 binary criterion.

### Implementation for User Story 2

- [X] T016 [P] [US2] Create `apps/frontend/lib/signalExplanations.ts` per data-model.md §1 and contracts/signal_explanations.contract.md. Includes: `ExplanationCopy` interface, `SignalName` union, `SIGNAL_EXPLANATIONS` Record covering all 11 names from FR-006, `FALLBACK_EXPLANATION`, `JARGON_BLACKLIST` regex array, `explainSignal(name: string)` function. Draft pt-BR content per research.md R6.
- [X] T017 [P] [US2] Create `apps/frontend/components/ExpandedAnalysis.tsx` per data-model.md §4. Renders `<div className="expanded-analysis">` with a `<ul>` of `<li><strong>{headline}</strong><p>{body}</p></li>` per dominant_signal. Empty-state message when no signals.
- [X] T018 [US2, depends on T016+T017] Modify `apps/frontend/components/GameRow.tsx`: add `expanded` local state per data-model.md §3. Wrap the row's clickable area in `<button aria-expanded={expanded} aria-controls={...}>` (only when `game.status === "done"`). Render `<ExpandedAnalysis game={game} />` conditionally inside the card when `expanded === true`. Cards in `pending`/`analyzing`/`error` retain current behavior (not clickable for expand).

**Checkpoint**: US2 functional + tested. Cards expand with pt-BR explanations.

---

## Phase 5: User Story 3 - Sticky Header (Priority: P2)

**Goal**: Replace the hero-section search form with a sticky header at top of viewport carrying brand + search + platform toggle. Mobile stacking (< 480px).

**Independent Test**: Render the page, scroll to bottom of results — header with brand + search remains visible. Resize to < 480px viewport — brand stacks above search.

### Tests for User Story 3

- [X] T019 [P] [US3] Write `apps/frontend/tests/e2e/fixtures/clean-3-games.txt`: 3 low-score games. Used for testing scroll behavior without expanded cards interfering.
- [X] T020 [P] [US3] Write `apps/frontend/tests/e2e/sticky-header.spec.ts` covering US3 AS1, AS2, AS3, AS4, AS5: (a) header visible after scroll, (b) hero section still appears initially below header, (c) expanded card content not hidden behind header, (d) mobile (< 480px) stacks vertically with both controls accessible, (e) clicking HorseLabs brand resets (sessions cleared, hero returns).

### Implementation for User Story 3

- [X] T021 [P] [US3] Create `apps/frontend/components/Header.tsx` per data-model.md §5. Sticky `position: fixed; top: 0; inset-x: 0; z-index: 50` per research.md R4. Desktop layout (≥ 768px): brand left, search + platform toggle right. Mobile layout (< 480px): brand row 1, search + toggle row 2. Brand click calls `useAnalysisContext().reset()` per Clarifications. Uses `--header-h` CSS custom property for `main` padding.
- [X] T022 [US3, depends on T021] Modify `apps/frontend/app/page.tsx`: render `<Header />` at top of return; remove the hero-section search `<form>` (still keep the hero's HorseLabs lockup + tagline for initial-state visual); `main` element gets `padding-top: var(--header-h)`. Verify hero appears only when `sessions.length === 0`.
- [X] T023 [US3, depends on T021] Modify `apps/frontend/app/layout.tsx` (or page-level CSS file): inject the `--header-h` CSS custom property with `64px` desktop + `112px` mobile (media query at 480px breakpoint).

**Checkpoint**: US3 functional + tested. Header sticky on scroll, mobile stacks, brand resets.

---

## Phase 6: User Story 4 - Cross-Viewport Bug Hunt (Priority: P2)

**Goal**: Playwright config with 4 viewport projects + bug detector suite + CI integration.

**Independent Test**: `npm run test:e2e` runs locally in ≤ 5 min, all viewport projects green, `playwright-report/` populated.

### Implementation for User Story 4

- [X] T024 [US4] Create `apps/frontend/playwright.config.ts` per contracts/playwright_e2e.contract.md §"Viewport matrix" + §"webServer config": 4 projects (`mobile-iphone-se`, `mobile-iphone-11-pro-max`, `desktop-1280`, `desktop-1920`), `webServer.command = "npm run dev"`, `webServer.timeout = 30_000`, `outputDir = "playwright-report"`, `use.trace = "retain-on-failure"`, `use.screenshot = "only-on-failure"`.
- [X] T025 [US4, depends on T009] Create `apps/frontend/tests/e2e/viewports.ts`: exports `VIEWPORT_NAMES = ['mobile-iphone-se', 'mobile-iphone-11-pro-max', 'desktop-1280', 'desktop-1920'] as const` and helper `runForEachViewport(spec, fn)` used by detector tests.
- [X] T026 [US4, depends on T024] Write `apps/frontend/tests/e2e/smoke.spec.ts`: navigates to `/`, asserts Header is visible, asserts no console errors. Runs against all 4 viewports.
- [X] T027 [US4, depends on T024] Write `apps/frontend/tests/e2e/bug-detectors.spec.ts` per contracts/playwright_e2e.contract.md §"Bug detector classes" + research.md R8: **6 detector tests** BD-1 through BD-6. BD-1..BD-5 per FR-013 (overflow, hidden controls, truncation, hover-on-touch, scroll lock). **BD-6 (layout shift on expand/collapse, closes F2/SC-008)**: snapshot bounding rects of non-expanded GameRow siblings before clicking a card to expand; assert max `|delta_y|` < 5px after expand and after collapse. Each detector runs against all 4 viewports.
- [X] T028 [US4, depends on T024+T027] **(closes F1/SC-005)** Two-pass shakedown of bug detectors:

  **Pass 1 — natural bug hunt**: Run `cd apps/frontend && npm run test:e2e` locally; iterate on bugs surfaced (any FR-013/BD class). If a real bug is found in US1/US2/US3 implementation, fix it in the corresponding component. Document each fix in the PR description. **Boundary**: if > 3 bugs per class are found, STOP and open a follow-up issue for the excess; do NOT extend T028 indefinitely.

  **Pass 2 — synthetic-regression validation of detectors**: For each of BD-1..BD-6, briefly introduce a regression in a throwaway local commit (do NOT push or merge):
    - BD-1 overflow: widen a fixed `min-width` element past viewport.
    - BD-2 hidden control: bump `<Header z-index>` above any button that should remain reachable.
    - BD-3 truncation: remove `text-overflow: ellipsis` from a constrained label.
    - BD-4 hover-on-touch: add a `:hover`-only style required for interaction.
    - BD-5 scroll lock: add `overflow: hidden` to `<html>` on expand.
    - BD-6 layout shift: change card expand from "render below" to "insert before with no reserved space".

    Confirm each detector fires with a clear diagnostic. Revert the regression. Embed the validation log (which detector fired for which regression) in the PR description for SC-005 sign-off.
- [X] T029 [US4, depends on T028] Modify `.github/workflows/ci.yml`: add `frontend_e2e` job per research.md R7. Path filter via `contains(toJson(github.event.pull_request.files.*.filename), 'apps/frontend')`. Cache Playwright browsers via `actions/cache@v4`. Job steps: checkout → setup-node → `npm ci` → cache restore → `npx playwright install` → `npm run lint` → `npm run type-check` → `npm run test:e2e`. Upload `playwright-report/` artifact on every run (success or failure). Timeout 12 min.

**Checkpoint**: US4 functional. CI gate active.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: CHANGELOG, scope-fence verification, final review.

- [X] T030 [P] Modify `CHANGELOG.md` at repo root: add entry under `## [Unreleased]` for feature 006 — list US1/US2/US3/US4 deliverables, mention no backend changes (FR-017), reference HANDOFF status if any item gets descoped during implementation.
- [X] T031 Verify FR-017 / SC-007 scope-fence: run `git diff --stat origin/main | awk '{print $1}' | sort -u | grep -vE '^(apps/frontend/|\.github/workflows/ci\.yml|CHANGELOG\.md|specs/006-frontend-ux-improvements/)$'`. Expected output: empty. If any line prints, scope was violated — investigate and rollback.
- [X] T032 Run `cd apps/frontend && npm run lint && npm run type-check && npm run test:e2e` from a fresh checkout. All three MUST pass. Coverage of new modules is implicit via Playwright suite (no separate coverage gate for frontend in CI today; may be a follow-up).
- [ ] T033 Execute `specs/006-frontend-ux-improvements/quickstart.md` §End-to-end smoke walkthrough manually on a fresh checkout. Document any deviations in the PR description. This is the human user-acceptance test for US1/US2/US3 (the per-spec automated tests cover US4).
- [X] T034 Final review against constitution: Principle I (lint/type clean, no transitive runtime bloat — only `@playwright/test` added at devDep level), Principle II (Playwright suite is the testing artifact — confirmed coverage of US1-US4 acceptance scenarios), Principle III (semantic `<button>` not `<div>`, JSON envelope unchanged, no CLI flag changes), Principle IV (5-min Playwright budget verified via T028 + CI run-time). Sign off in PR description.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. T005 BLOCKS US1 (needs `runAnalysis` from context) AND US3 (needs same).
- **US1 (Phase 3)**: Depends on Foundational. Tests + impl independent of US2/US3/US4.
- **US2 (Phase 4)**: Depends on Foundational only — works against the existing search flow (US3 not required). Independently testable.
- **US3 (Phase 5)**: Depends on Foundational. Independent of US1/US2 implementation, but US3 layout changes are tested by US4 detectors.
- **US4 (Phase 6)**: Depends on Foundational + needs T009 (mock-stream helper) which lands in US1. Bug detectors validate US1/US2/US3 outputs.
- **Polish (Phase 7)**: Depends on all stories complete.

### User Story Dependencies

- **US1 (P1)** depends on T005-T007 (context). Independently testable.
- **US2 (P1)** depends on T005-T007. Independently testable.
- **US3 (P2)** depends on T005-T007. Independently testable.
- **US4 (P2)** depends on T009 (mock-stream helper, lives in US1's tasks). Validates US1+US2+US3 outputs.

### Within Each User Story

- US1: tests (T008/T009/T010) ∥ impl (T011/T012). Tests reference impl by import name; can be written first.
- US2: tests (T013/T014/T015) ∥ impl (T016/T017/T018).
- US3: tests (T019/T020) ∥ impl (T021/T022/T023).
- US4: T024 (config) → T025 (viewports util) → tests (T026/T027) → local run (T028) → CI wire (T029).

### Parallel Opportunities

- **Phase 1**: T002 + T003 parallel (different domains: browsers vs lint config).
- **Phase 2**: sequential by nature (T005 → T006 → T007).
- **Across stories**: US1 + US2 + US3 can run on three parallel branches/developers after Foundational. US4 partial overlap: T024+T025 can start as soon as T009 exists.
- **Within stories**: tests and impl pairs are mostly [P] to each other (different files).

---

## Parallel Example: 3 P1+P2 stories simultaneous

```bash
# After T005-T007 complete:

# Developer A — US1:
T008 ∥ T009  →  T010 (test)  ∥  T011 (impl)  →  T012 (wire)

# Developer B — US2:
T013 ∥ T014 ∥ T015 (tests)  ∥  T016 ∥ T017 (impl)  →  T018 (wire)

# Developer C — US3:
T019 ∥ T020 (tests)  ∥  T021 (impl)  →  T022 ∥ T023 (wire)

# After all above complete — Developer D — US4:
T024 → T025 → T026 ∥ T027 → T028 → T029 (CI)

# Polish (any developer):
T030 ∥ T031 → T032 → T033 → T034
```

---

## Implementation Strategy

### MVP First (US1 + US2 — both P1)

1. Phase 1 (Setup) + Phase 2 (Foundational).
2. Phase 3 (US1) — player links unlock pivot navigation.
3. Phase 4 (US2) — expanded cards unlock layperson comprehension.
4. **STOP and VALIDATE**: human walkthrough of US1+US2 in dev mode. If MVP slice is sufficient for current users, ship US3+US4 as a follow-up PR.
5. Otherwise continue Phase 5 (US3) + Phase 6 (US4).

### Incremental Delivery (US3 + US4 as follow-up — optional)

Each P2 story can ship as a separate small PR:

- PR 1 (this MVP): Phase 1-4 (Setup + Foundational + US1 + US2) + Polish.
- PR 2: Phase 5 (US3 sticky header) — small, focused refactor.
- PR 3: Phase 6 (US4 Playwright + CI) — infrastructure work. Cross-validates PR 1 + PR 2 retroactively if executed in PR 1/2's branch via local `npx playwright test` runs.

### Parallel Team Strategy

With 3 developers:

- Dev A: Phase 1+2 (foundational); then US1 (T008-T012).
- Dev B: US2 (T013-T018) after Phase 2.
- Dev C: US3 (T019-T023) after Phase 2; then US4 (T024-T029) after T009 lands.
- All converge for Polish (T030-T034).

---

## Notes

- [P] tasks = different files, no dependencies.
- [Story] label maps task to specific user story for traceability.
- Each user story is independently completable and testable post-Foundational.
- FR-017 / SC-007 fence: any diff outside `apps/frontend/` + `.github/workflows/ci.yml` + `CHANGELOG.md` + `specs/006-frontend-ux-improvements/` is a scope violation. T031 enforces.
- Constitution Principle II spirit: Playwright suite covers UX-facing acceptance for US1-US4; signal-explanations.spec.ts covers SC-002 binary criterion. No unit-test gap blocks merge since the feature is presentation-layer only.
- Commit after each task or logical group; use Spec Kit commit prefix.
- Stop at the MVP checkpoint (post-US2) to validate before scope expansion.
- Avoid: vague tasks, cross-file conflicts on `GameRow.tsx` (T012 + T018 both touch it — execute serially within a single PR if Phase 3 + 4 land together).
