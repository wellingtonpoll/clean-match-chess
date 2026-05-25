// Feature 006 / T009 — Mocks the `/api/analyze` SSE response with a fixture file.
//
// Used by every spec file in this suite to isolate UI-layer bugs from
// upstream (chess.com / Stockfish) failures (FR-016).

import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import type { Page } from '@playwright/test'
import type { PlayerProfile } from '../../lib/profileTypes'

export type MockStreamScenario =
  | 'clean-3-games'
  | 'mixed-5-games'
  | 'suspect-1-game'
  | 'error-upstream'
  | 'long-signals'

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

  // Profile route is stubbed by default so that every spec that triggers
  // an analysis also gets a deterministic hero swap. Specs that need
  // a different profile (404, override) can call `mockProfile(...)`
  // after `mockStream(...)` to replace this default.
  await mockProfile(page)
}

/** Default profile served by `mockProfile()` when no override is supplied.
 *  Matches the chess.com-flavoured envelope normalised by /api/profile. */
export const DEFAULT_PROFILE: PlayerProfile = {
  username: 'daianydias',
  platform: 'chesscom',
  url: 'https://www.chess.com/member/daianydias',
  avatarUrl: undefined,
  country: 'BR',
  title: undefined,
  displayName: 'Daiany Dias',
  joinedAt: 1_577_836_800, // 2020-01-01
  ratings: [
    { mode: 'rapid', rating: 1480, games: 312 },
    { mode: 'blitz', rating: 1395, games: 1204 },
    { mode: 'bullet', rating: 1320, games: 880 },
    { mode: 'daily', rating: 1510, games: 22 },
  ],
}

export async function mockProfile(
  page: Page,
  override: Partial<PlayerProfile> = {},
  status: number = 200
): Promise<void> {
  await page.route('**/api/profile**', async (route) => {
    if (status >= 400) {
      await route.fulfill({
        status,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: status === 404 ? 'not_found' : 'upstream_failure',
          message: status === 404 ? 'player not found (mock)' : `upstream ${status} (mock)`,
        }),
      })
      return
    }
    await route.fulfill({
      status: 200,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...DEFAULT_PROFILE, ...override }),
    })
  })
}
