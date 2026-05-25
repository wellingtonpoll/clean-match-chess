# Phase 0 Research — Feature 006 (Frontend UX Improvements)

**Branch**: `006-frontend-ux-improvements` | **Date**: 2026-05-24

Resolves the open technical decisions for Phase 1 design. Decision / Rationale / Alternatives format per skill convention.

---

## R1 — Playwright vs alternatives for cross-viewport bug hunt

**Decision**: Use **`@playwright/test`** v1.49+ for the E2E suite. Configure projects per viewport via `playwright.config.ts`.

**Rationale**:
- First-class TypeScript support; matches the React 19 + TS 5.8 stack already in `apps/frontend`.
- Built-in device descriptors (`devices['iPhone SE']`, `devices['iPhone 11 Pro Max']`) match the viewport sizes spec'd in FR-012.
- Route interception (`page.route()`) is the simplest way to stub `/api/analyze` without standing up an MSW worker.
- Headless mode is default; can opt into headed for local debugging. Native screenshot/video capture for FR-015.
- No browser version drift: Playwright pins Chromium/WebKit/Firefox versions per `@playwright/test` release.
- Active maintenance, large ecosystem, well-known patterns for Next.js apps (`playwright dev` integration via `webServer` config).

**Alternatives considered**:
- *Cypress*: rejected. Single-browser-by-default (Chromium), iframe-based mobile emulation less faithful, slower for parallel viewport runs.
- *Puppeteer*: rejected. Chromium only; requires manual test runner harness; no built-in viewport projects.
- *Vitest browser mode + happy-dom*: rejected. happy-dom doesn't render layout dimensions accurately enough for overflow detection.
- *Manual cross-browser testing*: rejected. SC-005 requires CI-blocking detection of 5 bug classes; manual is not automatable.

---

## R2 — `/api/analyze` SSE mock strategy in Playwright

**Decision**: Use **Playwright `page.route('**/api/analyze**', ...)`** to intercept the request and return a pre-canned `text/event-stream` response from a fixture file at `apps/frontend/tests/e2e/fixtures/mock-stream-<scenario>.txt`.

**Rationale**:
- Zero infrastructure setup (no MSW worker, no Service Worker registration in tests).
- Deterministic — each test scenario picks a fixture; no race conditions with the real backend.
- Per FR-016, isolates layout bugs from upstream (chess.com / Stockfish) failures.
- Allows scripting edge-case payloads (e.g., a card with a "high" risk + 3 dominant_signals to validate the expanded layout).

**Fixture format**:

```text
data: {"idx": 0, "status": "done", "score": 0.87, "risk_level": "high", "confidence_interval": [0.82, 0.92], "dominant_signals": ["acpl-analysis", "engine-correlation/top1"], "headers": {"White": "alice123", "Black": "bob456", "Date": "2026-04-15", "TimeControl": "600+0", "Result": "1-0"}, "ply_count": 45, "run_id": "abc123"}

data: {"idx": 1, "status": "done", "score": 0.12, "risk_level": "low", "confidence_interval": [0.05, 0.18], "dominant_signals": [], "headers": {"White": "bob456", "Black": "alice123", "Date": "2026-04-16", "Result": "0-1"}}

data: {"done": true}
```

Helper `mockStream(page, scenario)` in `apps/frontend/tests/e2e/mock-stream.ts` reads the fixture, formats the response, and registers the route.

**Alternatives considered**:
- *MSW (Mock Service Worker)*: rejected. Adds service-worker complexity; Playwright route interception is simpler and covers the same use case.
- *Local Express stub server*: rejected. Adds process-management to CI; route interception is in-process.

---

## R3 — Add ESLint for frontend lint parity with backend ruff gate

**Decision**: Add **flat-config ESLint** (`eslint.config.js`) with `@typescript-eslint`, `eslint-plugin-react`, `eslint-plugin-react-hooks`, `eslint-plugin-jsx-a11y`, and Next.js's recommended preset.

**Rationale**:
- Backend has `ruff check + ruff format --check + mypy --strict` as CI gates (Principle I — Code Quality). The frontend currently has zero lint/type gate beyond `tsc --noEmit` (referenced as `npm run type-check` but not wired to CI). This feature surfaces this gap.
- `jsx-a11y` is critical for the spec's a11y commitments (button vs div, aria-expanded).
- Flat config is the current default in ESLint 9.x; the existing `package.json` doesn't pin ESLint, so a fresh install picks the modern config.

**Alternatives considered**:
- *Biome*: rejected for this feature. Performance-attractive but `next lint` is the conventional path for Next.js apps + the a11y plugin ecosystem is more mature on ESLint.
- *No lint added*: rejected. Would violate Principle I parity ("Linting MUST pass before merge"). Adding it now is cheap and prevents a follow-up debt task.

**Scope note**: Adding ESLint is a Phase 1 deliverable but the linting *gate* in CI is added in the new `frontend_e2e` job (or alongside it). Existing `apps/frontend` code may have lint debt — first run will produce a baseline; fixes go in the same PR.

---

## R4 — Sticky header CSS strategy

**Decision**: Use `position: fixed; top: 0; left: 0; right: 0; z-index: 100;` via inline styles or a Tailwind utility class (`fixed top-0 inset-x-0 z-50`). Main content gets `padding-top: <header-height>` via CSS custom property `--header-height` to avoid content sitting behind the header.

**Rationale**:
- `position: sticky` would only stick within a scroll container; we need viewport-level stickiness regardless of internal containers.
- Z-index 100 (or Tailwind `z-50`) is high enough to clear normal content but conventional enough not to conflict with future modals (`z-50`).
- CSS custom property for height lets the mobile stacking layout (taller header) push content correctly without JS measurements.

**Mobile stacking implementation**:

```tsx
<header
  className="fixed top-0 inset-x-0 z-50 bg-[#0B0B0D] border-b border-[rgba(242,239,232,0.14)]"
  style={{ '--header-h': '64px' } as React.CSSProperties}
>
  <div className="hidden md:flex ...">{/* desktop: brand | search */}</div>
  <div className="flex md:hidden flex-col ...">{/* mobile: brand row, search row */}</div>
</header>
<main style={{ paddingTop: 'var(--header-h)' }}>...</main>
```

Mobile header height ≈ 112 px (2 stacked rows × ~56 px); desktop ≈ 64 px. Custom property is updated by a media query in CSS or branches inline.

**Alternatives considered**:
- *Pure `position: sticky`*: rejected. Behaves unpredictably if a parent has `overflow: hidden` or similar.
- *JavaScript-measured header height*: rejected. Layout shift risk + adds runtime cost for a static value.

---

## R5 — Player link click semantics + state lifting

**Decision**: Extract `runAnalysis` + relevant state (`username`, `platform`, `sessions`, `activeUsername`, `isAnalyzing`, `abortRef`) from `app/page.tsx` into a **React context** (`AnalysisContext`) provided in `layout.tsx`. Header (search field) and GameRow (player link) both consume the context — `header.search.submit()` and `playerLink.onClick(username)` both call `runAnalysis(0, { newUsername })`.

**Rationale**:
- Prop drilling from `page.tsx` → `GameRow` → player name (3 levels) for `runAnalysis` is awkward.
- Context provider scoped to the page (or layout) avoids global state library overhead.
- Same context covers the future need where `Header` needs to read `isAnalyzing` for the button disabled state.

**Player link no-op**:

```tsx
function PlayerLink({ username, isSubject }: Props) {
  const { activeUsername, platform, runAnalysis, isAnalyzing } = useAnalysisContext();
  const sameAsActive = username === activeUsername;

  if (sameAsActive) {
    return <span className="player-name player-name--self">{username}</span>;
  }

  return (
    <button
      type="button"
      className="player-name player-name--link"
      onClick={() => runAnalysis(0, { newUsername: username })}
      disabled={isAnalyzing && username === activeUsername}
    >
      {username}
    </button>
  );
}
```

**Alternatives considered**:
- *Zustand / Jotai*: rejected. Overkill for one page's state; one more dep to maintain.
- *useState in page.tsx + prop drilling*: rejected per ergonomic concern above.
- *URL-state via Next.js router*: deferred. Would enable back-button navigation but adds scope; per FR-017 + plan summary, URL changes are out of this feature (follow-up).

---

## R6 — Signal explanation dictionary content + jargon blacklist

**Decision**: 11 signal entries in `apps/frontend/lib/signalExplanations.ts` as a typed `Record<string, ExplanationCopy>` where `ExplanationCopy = { headline: string; body: string; }`. Headline is 3-5 words (signal name in lay terms); body is 1-2 sentences explaining what the signal measures.

**Jargon blacklist** (enforced by `signal-explanations.spec.ts`):
- `z-score`
- `bootstrap`
- `CUSUM`
- `ratio` standing alone (must appear with context like "razão entre A e B")
- `p-value`
- `regression residual` (in English; pt-BR "resíduo de regressão" allowed if defined inline)
- `bucket` standing alone (must appear in pt-BR as "faixa de rating")

**Example entries** (draft):

```ts
export const SIGNAL_EXPLANATIONS = {
  "acpl-analysis": {
    headline: "Precisão acima do esperado",
    body: "Em média, este jogador erra muito menos centipawns por lance do que jogadores da mesma faixa de rating. Diferenças grandes sugerem ajuda de motor.",
  },
  "engine-correlation/top1": {
    headline: "Lances batem com o motor",
    body: "Fração dos lances jogados que coincidem com a melhor opção do Stockfish. Valores muito acima da média da faixa de rating indicam correlação suspeita.",
  },
  // ... 9 more
};
```

**Rationale**:
- Maintaining the dictionary in the frontend (not the backend) keeps presentation copy separate from algorithm code. Adding a new signal in the backend doesn't require coordinated frontend deploy — the fallback covers the gap.
- Jargon blacklist makes SC-002 (rewritten) automatically verifiable.
- pt-BR is the project's user-facing language per existing UI strings.

**Alternatives considered**:
- *Server-supplied explanations (JSON in `/api/analyze` response)*: rejected. Couples backend deploys to UX copy. The signal name is the stable contract; the explanation is presentation.
- *External translation service (Lokalise, Crowdin)*: rejected. Overkill for 11 strings; no near-term i18n requirement beyond pt-BR.

---

## R7 — `frontend_e2e` CI job design

**Decision**: New job in `.github/workflows/ci.yml`:

```yaml
frontend_e2e:
  if: |
    contains(toJson(github.event.pull_request.files.*.filename), 'apps/frontend')
    || github.event_name == 'push'
  runs-on: ubuntu-latest
  timeout-minutes: 12
  needs: test
  steps:
    - uses: actions/checkout@v6
    - uses: actions/setup-node@v4
      with: { node-version: '20' }
    - working-directory: apps/frontend
      run: npm ci
    - name: Cache Playwright browsers
      uses: actions/cache@v4
      with:
        path: ~/.cache/ms-playwright
        key: playwright-${{ hashFiles('apps/frontend/package-lock.json') }}
    - working-directory: apps/frontend
      run: npx playwright install --with-deps chromium webkit
    - working-directory: apps/frontend
      run: npm run lint
    - working-directory: apps/frontend
      run: npm run type-check
    - working-directory: apps/frontend
      run: npm run test:e2e
    - uses: actions/upload-artifact@v4
      if: always()
      with:
        name: playwright-report
        path: apps/frontend/playwright-report/
```

**Rationale**:
- Path filter via `contains(toJson(github.event.pull_request.files.*.filename), 'apps/frontend')` matches the spec's FR-018 + SC-006. (Note: GitHub's `paths:` workflow-level filter would skip the entire workflow; we want the workflow to run but this job to conditionally execute.)
- Cache key on `package-lock.json` covers Playwright version pinning indirectly.
- `chromium webkit` covers desktop + iOS Safari behaviors; Firefox omitted for budget. Can add later if a Firefox-specific bug surfaces.
- `--with-deps` installs system libraries needed by browser binaries on Ubuntu runners.
- 12-min timeout = 5-min budget per SC-004 + 7-min headroom for cold cache + install.

**Alternatives considered**:
- *Workflow-level `paths:` filter*: rejected. Skips the entire workflow on non-frontend PRs, which prevents other jobs (test, design_system_audits) from running.
- *Separate workflow file `.github/workflows/frontend-e2e.yml`*: cleaner but adds workflow proliferation. Single-workflow approach matches existing `fpr_gate` pattern from feature 005.

---

## R8 — Bug detector implementation specifics (FR-013)

**Decision**: Each detector is a Playwright `expect`-style assertion run inside `bug-detectors.spec.ts` against every viewport project:

1. **Overflow detector**: `await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBe(0)`. Fails with element-level diagnostic via `page.evaluate` scanning for `el.scrollWidth > el.clientWidth`.
2. **Hidden controls detector**: For each `<button>` and `<a>` in the page, `boundingClientRect` is checked against the viewport. If `top < header_height && z-index < header_z_index`, fail with element selector.
3. **Truncation detector**: Find elements where `scrollWidth > clientWidth + 2` (text overflow without ellipsis). Allowed if computed CSS has `text-overflow: ellipsis`. Fail otherwise.
4. **Hover-on-touch detector**: Tap each hoverable element with touch input; if hover style isn't reachable via `:hover` on touch but functionality requires it (e.g., tooltip-only), fail.
5. **Scroll lock detector**: After expanding a card, `page.evaluate(() => window.scrollY)` should remain accessible; assert document scrollHeight is still > viewport height (i.e., page is still scrollable).

**Rationale**:
- Each assertion is concrete and produces a screenshot on failure (Playwright's default trace + screenshot config).
- Detectors are colocated in one file for shared setup (each runs against the same mocked page state).

**Alternatives considered**:
- *Axe-core for full a11y audit*: deferred to a follow-up. Axe is great but adds 100+ rules; this feature targets 5 layout bug classes specifically. A complementary `axe.spec.ts` can land later.

---

## Summary

All eight research decisions resolved. No outstanding `NEEDS CLARIFICATION` markers. Phase 1 design can proceed.
