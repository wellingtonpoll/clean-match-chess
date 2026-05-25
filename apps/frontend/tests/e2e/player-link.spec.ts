// Feature 006 / T010 — US1 acceptance: player names as clickable links.

import { test, expect } from '@playwright/test'
import { mockStream } from './mock-stream'

test.describe('US1 — clickable player links', () => {
  test('clicking opponent name re-triggers analysis with that username (US1 AS1)', async ({
    page,
  }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')

    // Initial analysis for alice123.
    await page.getByPlaceholder('Nome de usuário...').fill('alice123')
    await page.getByRole('button', { name: /^Analisar$/i }).click()

    // Wait for at least one finished game card to render.
    await expect(page.getByTestId('player-link').first()).toBeVisible({ timeout: 8000 })

    // bob456 appears in the fixture; click the PlayerLink button (not the
    // outer GameRow toggle, which inherits the same accessible name via ARIA
    // name computation). Use data-testid to disambiguate.
    const bobLink = page
      .locator('[data-testid="player-link"]', { hasText: 'bob456' })
      .first()
    await bobLink.click()

    await expect(page.getByPlaceholder('Nome de usuário...')).toHaveValue('bob456')
  })

  test('subject name renders as plain text, not a button (US1 AS3)', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')

    await page.getByPlaceholder('Nome de usuário...').fill('alice123')
    await page.getByRole('button', { name: /^Analisar$/i }).click()

    // Wait for the analysis subject header to appear ("alice123").
    await expect(page.getByRole('heading', { name: 'alice123' })).toBeVisible({
      timeout: 8000,
    })

    // The subject's own name in game cards must be rendered as a span,
    // not a button. We assert at least one player-link-self testid exists.
    await expect(page.getByTestId('player-link-self').first()).toBeVisible()

    // And there must be NO interactive <button> data-testid="player-link"
    // bearing the subject's name.
    await expect(
      page.locator('[data-testid="player-link"]', { hasText: 'alice123' })
    ).toHaveCount(0)
  })

  test('opponent links use semantic <button>, not <div onClick> (FR-001)', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')

    await page.getByPlaceholder('Nome de usuário...').fill('alice123')
    await page.getByRole('button', { name: /^Analisar$/i }).click()

    await expect(page.getByTestId('player-link').first()).toBeVisible({ timeout: 8000 })

    // First testid="player-link" must be a real <button> for a11y compliance.
    const tagName = await page.getByTestId('player-link').first().evaluate((el) => el.tagName)
    expect(tagName).toBe('BUTTON')
  })
})
