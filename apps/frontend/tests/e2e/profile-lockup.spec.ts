// Profile-lockup spec — hero section now stays mounted after a search and
// renders the searched player's profile + ratings. Adds coverage for the
// happy path, the 404 path, and the brand-reset flow that restores the
// default hero.

import { test, expect } from '@playwright/test'
import { DEFAULT_PROFILE, mockProfile, mockStream } from './mock-stream'

test.describe('Hero — searched-user profile lockup', () => {
  test('default hero renders before any search', async ({ page }) => {
    await page.goto('/')
    const hero = page.getByTestId('hero')
    await expect(hero).toBeVisible()
    await expect(hero).toHaveAttribute('data-mode', 'default')
    // ProfileLockup must not be mounted on cold load.
    await expect(page.getByTestId('profile-lockup')).toHaveCount(0)
  })

  test('hero swaps to profile lockup on submit and stays mounted', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('daianydias')
    await page.getByTestId('header-search-submit').click()

    const hero = page.getByTestId('hero')
    await expect(hero).toHaveAttribute('data-mode', 'profile')
    await expect(page.getByTestId('profile-lockup')).toBeVisible()
    await expect(page.getByTestId('profile-username')).toHaveText(DEFAULT_PROFILE.username)
    await expect(page.getByTestId('profile-platform')).toHaveText('chess.com')

    // All four ratings from DEFAULT_PROFILE render.
    const ratings = page.getByTestId('profile-rating')
    await expect(ratings).toHaveCount(DEFAULT_PROFILE.ratings.length)
    for (const r of DEFAULT_PROFILE.ratings) {
      await expect(
        page.locator(`[data-testid="profile-rating"][data-mode="${r.mode}"]`)
      ).toContainText(String(r.rating))
    }

    // Hero remains visible while the results section renders below.
    await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8000 })
    await expect(hero).toBeVisible()
  })

  test('hero renders not_found state when profile is 404', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await mockProfile(page, {}, 404) // override default
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('does-not-exist-12345')
    await page.getByTestId('header-search-submit').click()

    const err = page.getByTestId('profile-error')
    await expect(err).toBeVisible()
    await expect(err).toHaveAttribute('data-status', 'not_found')
  })

  test('profile hero stays pinned below header when scrolling results', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('daianydias')
    await page.getByTestId('header-search-submit').click()
    await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8000 })

    // Scroll the document so the natural hero position passes under
    // the viewport top.
    await page.evaluate(() => window.scrollTo(0, 1200))
    await page.waitForTimeout(80) // allow layout to settle

    const headerBox = await page.getByTestId('header').boundingBox()
    const heroBox = await page.getByTestId('hero').boundingBox()
    expect(headerBox).not.toBeNull()
    expect(heroBox).not.toBeNull()

    const headerBottom = (headerBox?.y ?? 0) + (headerBox?.height ?? 0)
    const heroTop = heroBox?.y ?? 0

    // Hero sticks immediately below the header (allow 2px for sub-pixel rounding).
    expect(Math.abs(heroTop - headerBottom)).toBeLessThanOrEqual(2)

    // Hero remains visible in the viewport.
    expect(heroTop).toBeGreaterThanOrEqual(0)
    expect(heroTop).toBeLessThan(200)
  })

  test('clicking brand resets hero to default mode', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('daianydias')
    await page.getByTestId('header-search-submit').click()
    await expect(page.getByTestId('profile-lockup')).toBeVisible()

    await page.getByTestId('header-brand').click()
    await expect(page.getByTestId('hero')).toHaveAttribute('data-mode', 'default')
    await expect(page.getByTestId('profile-lockup')).toHaveCount(0)
  })
})
