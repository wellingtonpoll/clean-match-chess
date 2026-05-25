# Quickstart — Feature 006 (Frontend UX Improvements)

**Branch**: `006-frontend-ux-improvements` | **Date**: 2026-05-24

Maintainer-facing recipes for running the dev server, running the Playwright suite, and adding new signal explanations.

---

## 1. Run the dev server

```bash
cd apps/frontend
npm install         # one-time
npm run dev
```

Opens at `http://localhost:3000`. Hot-reload on file changes.

The backend `/api/analyze` route is served by a sibling Python process (see `apps/cli/`). For UI-only work, the Playwright mock stream is sufficient — no backend needed.

---

## 2. Run the E2E suite

### Local (first time)

```bash
cd apps/frontend
npm install
npx playwright install chromium webkit --with-deps
```

### Local (every run)

```bash
cd apps/frontend
npm run test:e2e                              # all viewports
npm run test:e2e -- --project=mobile-iphone-se  # one viewport
npm run test:e2e -- --ui                       # interactive mode
```

Expected wall time: < 5 min on a modern laptop.

Reports + screenshots land at `apps/frontend/playwright-report/`. Open `playwright-report/index.html` to inspect failures.

---

## 3. Add a new signal explanation

The backend emits a new signal name (e.g., `move-time-variance`) and you want to surface a layperson explanation.

```ts
// apps/frontend/lib/signalExplanations.ts

// 1. Add the name to the SignalName union:
export type SignalName =
  | /* ... existing */
  | "move-time-variance";

// 2. Add an entry to SIGNAL_EXPLANATIONS:
export const SIGNAL_EXPLANATIONS: Record<SignalName, ExplanationCopy> = {
  // ... existing
  "move-time-variance": {
    headline: "Variação anormal no tempo por lance",
    body: "Tempo gasto em cada lance varia menos do que o esperado para um jogador humano. Padrão consistente com consulta de motor.",
  },
};
```

Run the jargon-blacklist test:

```bash
npm run test:e2e -- --grep "signal-explanations"
```

If passes, the new signal is wired. If a card with that signal renders, the user sees the new pt-BR explanation; cards without it fall back gracefully.

---

## 4. Add a new bug detector

```ts
// apps/frontend/tests/e2e/bug-detectors.spec.ts

test('detector: my-new-class-of-bug', async ({ page }) => {
  await mockStream(page, 'mixed-5-games');
  await page.goto('/');
  // ... assertions
});
```

Test runs against all 4 viewport projects automatically. Update FR-013 count if you add a detector beyond the initial 5.

---

## 5. Add a new mock scenario

```bash
# apps/frontend/tests/e2e/fixtures/my-new-scenario.txt
data: {"idx": 0, "status": "done", "score": 0.5, ...}
data: {"done": true}
```

Use in tests:

```ts
await mockStream(page, 'my-new-scenario');
```

---

## 6. Verify FR-017 / SC-007 scope-fence

Before opening a PR, verify the diff is confined to frontend + spec + workflow + CHANGELOG:

```bash
git diff --stat origin/main | awk '{print $1}' | sort -u | grep -vE '^(apps/frontend/|\.github/workflows/ci\.yml|CHANGELOG\.md|specs/006-frontend-ux-improvements/)$'
```

Expected output: empty. Any line printed = scope violation.

---

## 7. CI: trigger the `frontend_e2e` job

The job runs automatically on PRs that touch `apps/frontend/**`. To force it on a PR that doesn't touch frontend, add a `frontend` label OR push a no-op commit that touches `apps/frontend/README.md` (if exists) to flip the path filter.

---

## End-to-end smoke (after all tasks complete)

```bash
cd apps/frontend
npm run lint       # ESLint clean
npm run type-check # tsc --noEmit clean
npm run test:e2e   # all viewports green
```

Then run the page in a real browser:

```bash
npm run dev
# open http://localhost:3000
```

Smoke walkthrough:
1. Header is visible at top with HorseLabs brand + search.
2. Type "magnuscarlsen" or similar valid Chess.com username, click Analisar.
3. Wait for first card to land.
4. Click the opponent's name in the card — re-analysis triggers for that player.
5. Click a card — expands with "Análise detalhada" + pt-BR text per signal.
6. Scroll down — header remains stuck to top.
7. Click "HorseLabs" — sessions clear, hero section returns.
8. Resize browser to < 480px — header stacks vertically; both controls accessible.
