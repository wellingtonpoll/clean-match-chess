// Feature 006 / T020 — US3 acceptance: sticky header + brand reset + mobile stacking.

import { test, expect } from '@playwright/test'
import { mockStream } from './mock-stream'

test.describe('US3 — sticky header', () => {
  test('header is visible on initial load (US3 AS2)', async ({ page }) => {
    await mockStream(page, 'clean-3-games')
    await page.goto('/')
    await expect(page.getByTestId('header')).toBeVisible()
    await expect(page.getByTestId('hero')).toBeVisible()
  })

  test('header remains visible after scrolling results (US3 AS1)', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('alice123')
    await page.getByTestId('header-search-submit').click()

    // Wait for at least one finished game card.
    await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8000 })

    // Scroll to bottom.
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))

    // Header still visible.
    const headerBox = await page.getByTestId('header').boundingBox()
    expect(headerBox?.y).toBeLessThan(50) // sticky → near top of viewport
  })

  test('clicking HorseLabs brand resets analysis (US3 AS5)', async ({ page }) => {
    await mockStream(page, 'mixed-5-games')
    await page.goto('/')
    await page.getByTestId('header-search-input').fill('alice123')
    await page.getByTestId('header-search-submit').click()

    await expect(page.getByRole('heading', { name: 'alice123' })).toBeVisible({ timeout: 8000 })

    await page.getByTestId('header-brand').click()

    // Hero returns, results vanish, input cleared.
    await expect(page.getByTestId('hero')).toBeVisible()
    await expect(page.getByTestId('header-search-input')).toHaveValue('')
    await expect(page.getByRole('heading', { name: 'alice123' })).toHaveCount(0)
  })

  test('mobile viewport stacks brand and search vertically (US3 AS4 / FR-011)', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 667 })
    await mockStream(page, 'clean-3-games')
    await page.goto('/')

    const brandBox = await page.getByTestId('header-brand').boundingBox()
    const formBox = await page.getByTestId('header-search-form').boundingBox()

    expect(brandBox).not.toBeNull()
    expect(formBox).not.toBeNull()
    // Brand row is ABOVE the form row.
    expect((brandBox?.y ?? 0) + (brandBox?.height ?? 0)).toBeLessThanOrEqual(
      formBox?.y ?? Number.POSITIVE_INFINITY
    )
  })
})
