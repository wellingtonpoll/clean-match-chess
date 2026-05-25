// Feature 006 / T026 — Smoke pass for each viewport project.

import { test, expect } from '@playwright/test'
import { mockStream } from './mock-stream'

test('hero + header render on initial load', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  page.on('console', (msg) => {
    if (msg.type() === 'error') errors.push(msg.text())
  })

  await mockStream(page, 'clean-3-games')
  await page.goto('/')

  await expect(page.getByTestId('header')).toBeVisible()
  await expect(page.getByTestId('hero')).toBeVisible()
  await expect(page.getByTestId('header-search-input')).toBeVisible()
  await expect(page.getByTestId('header-search-submit')).toBeVisible()

  // No client-side errors.
  expect(errors, errors.join('\n')).toEqual([])
})

test('search submit from header triggers analysis', async ({ page }) => {
  await mockStream(page, 'mixed-5-games')
  await page.goto('/')
  await page.getByTestId('header-search-input').fill('alice123')
  await page.getByTestId('header-search-submit').click()

  await expect(page.getByRole('heading', { name: 'alice123' })).toBeVisible({ timeout: 8000 })
  await expect(page.getByTestId('game-row').first()).toBeVisible()
})
