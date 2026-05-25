# Playwright E2E Contract — Feature 006

**Branch**: `006-frontend-ux-improvements`

Test invocation, viewport matrix, mock fixture format, CI integration. Consumed by `apps/frontend/playwright.config.ts` + every `*.spec.ts` under `apps/frontend/tests/e2e/`.

---

## Invocation

```bash
cd apps/frontend
npm run test:e2e                                    # all viewports, all specs
npm run test:e2e -- --project=desktop-1280          # single viewport
npm run test:e2e -- --grep "bug-detectors"          # single spec file
npm run test:e2e -- --ui                            # interactive UI mode (local dev only)
```

CI uses `npm run test:e2e` without flags (full matrix).

---

## Viewport matrix (FR-012)

```ts
// playwright.config.ts
projects: [
  {
    name: "mobile-iphone-se",
    use: { ...devices["iPhone SE"] },  // 375×667
  },
  {
    name: "mobile-iphone-11-pro-max",
    use: { ...devices["iPhone 11 Pro Max"] },  // 414×896
  },
  {
    name: "desktop-1280",
    use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } },
  },
  {
    name: "desktop-1920",
    use: { ...devices["Desktop Chrome"], viewport: { width: 1920, height: 1080 } },
  },
],
```

---

## webServer config

```ts
webServer: {
  command: "npm run dev",
  url: "http://localhost:3000",
  reuseExistingServer: !process.env.CI,
  timeout: 30_000,  // FR (acceptance scenario US4.5)
},
```

Playwright waits up to 30 s for `http://localhost:3000` to respond before running tests. Health check uses the dev server's HTTP 200 on `/`.

---

## Mock fixture format (FR-016)

Plain `.txt` file at `apps/frontend/tests/e2e/fixtures/<scenario>.txt`. Each line is a single SSE event:

```text
data: {"idx": 0, "status": "done", "score": 0.87, ...}
data: {"idx": 1, "status": "done", "score": 0.12, ...}
data: {"done": true}
```

Helper:

```ts
// apps/frontend/tests/e2e/mock-stream.ts
import { Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export async function mockStream(page: Page, scenario: string): Promise<void> {
  const body = readFileSync(
    join(__dirname, "fixtures", `${scenario}.txt`),
    "utf-8",
  );
  await page.route("**/api/analyze*", async (route) => {
    await route.fulfill({
      status: 200,
      headers: { "Content-Type": "text/event-stream" },
      body,
    });
  });
}
```

---

## Bug detector classes (FR-013)

| ID | Bug class | Implementation |
|---|---|---|
| BD-1 | Horizontal overflow | `document.documentElement.scrollWidth > viewport.width` |
| BD-2 | Hidden controls behind sticky header | each interactive element's bounding box vs header z-index |
| BD-3 | Text truncation without ellipsis | `el.scrollWidth > el.clientWidth + 2 && getComputedStyle(el).textOverflow !== "ellipsis"` |
| BD-4 | Hover-only state on touch | `:hover` style applied via mouse only; touch tap doesn't reach state |
| BD-5 | Scroll lock after expand | `document.body.scrollHeight > window.innerHeight` after expanding a card |

Each detector lives as a `test()` block in `bug-detectors.spec.ts`. Runs against every viewport project. Failure produces a screenshot under `playwright-report/`.

---

## Required test files

| File | Tests | Notes |
|---|---|---|
| `smoke.spec.ts` | Hero loads, Header renders, search submit works | Smoke pass for each viewport |
| `player-link.spec.ts` | US1 AS1, AS2, AS3, AS4 | Mocks `mixed-5-games` |
| `expand-card.spec.ts` | US2 AS1, AS2, AS3, AS4, AS5 | Mocks `suspect-1-game` |
| `sticky-header.spec.ts` | US3 AS1, AS2, AS3, AS4, AS5 | Scroll behavior + brand click |
| `bug-detectors.spec.ts` | BD-1 through BD-5 | Runs against `mixed-5-games` |
| `signal-explanations.spec.ts` | SC-002 binary (entries + pt-BR + jargon blacklist) | No page interaction; pure module test |

---

## CI integration (FR-018)

New job `frontend_e2e` in `.github/workflows/ci.yml`. Job spec in `research.md` R7.

- Triggers: any PR touching `apps/frontend/**` OR any push to `main`.
- Steps: `npm ci` → cache Playwright browsers → `npx playwright install` → `npm run lint` → `npm run type-check` → `npm run test:e2e`.
- Artifact: `playwright-report/` uploaded on every run (success or failure).
- Timeout: 12 min (5-min budget + 7-min headroom for cold install).

---

## Performance budget (SC-004 / Principle IV)

- Warm cache: ≤ 5 min wall time end-to-end (install browsers cached, dev server boot ≤ 30 s).
- Cold cache: ≤ 8 min wall time.
- Per-test soft budget: 30 s. Tests exceeding emit a warning to encourage tightening.

---

## Stability guarantees

- Tests are deterministic — same mock fixture, same viewport, same browser version ⇒ same result.
- Mock fixtures live under version control; any test that depends on a fixture references it by name (`scenario` parameter).
- Playwright pins browser versions; `package-lock.json` ensures consistent installs across machines.
- No network calls during tests (route interception covers `/api/analyze`; static assets served by Next.js dev server in-process).
