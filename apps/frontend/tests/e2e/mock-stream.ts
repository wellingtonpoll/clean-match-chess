// Feature 006 / T009 — Mocks the `/api/analyze` SSE response with a fixture file.
//
// Used by every spec file in this suite to isolate UI-layer bugs from
// upstream (chess.com / Stockfish) failures (FR-016).

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Page } from '@playwright/test'

export type MockStreamScenario =
  | 'clean-3-games'
  | 'mixed-5-games'
  | 'suspect-1-game'
  | 'error-upstream'

const FIXTURES_DIR = join(__dirname, 'fixtures')

export async function mockStream(page: Page, scenario: MockStreamScenario): Promise<void> {
  const body = readFileSync(join(FIXTURES_DIR, `${scenario}.txt`), 'utf-8')

  await page.route('**/api/analyze**', async (route) => {
    await route.fulfill({
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
      },
      body,
    })
  })
}
