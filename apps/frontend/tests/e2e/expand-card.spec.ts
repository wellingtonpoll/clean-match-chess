// Feature 006 / T014 — US2 acceptance: expandable cards with pt-BR explanations.

import { test, expect, type Page } from '@playwright/test'
import { mockStream, type MockStreamScenario } from './mock-stream'

async function runAnalysis(
  page: Page,
  scenario: MockStreamScenario,
  username = 'alice123'
): Promise<void> {
  await mockStream(page, scenario)
  await page.goto('/')
  await page.getByPlaceholder('Nome de usuário...').fill(username)
  await page.getByRole('button', { name: /^Analisar$/i }).click()
}

test.describe('US2 — expandable cards', () => {
  test('expand card reveals pt-BR explanation per signal (US2 AS1)', async ({ page }) => {
    await runAnalysis(page, 'suspect-1-game')
    await expect(page.getByTestId('game-row__toggle').first()).toBeVisible({ timeout: 8000 })

    await page.getByTestId('game-row__toggle').first().click()

    await expect(page.getByTestId('expanded-analysis')).toBeVisible()
    // 3 signals in the fixture → 3 explanation blocks.
    await expect(page.getByTestId('signal-explanation')).toHaveCount(3)
  })

  test('click toggles collapse (US2 AS2)', async ({ page }) => {
    await runAnalysis(page, 'suspect-1-game')
    const toggle = page.getByTestId('game-row__toggle').first()
    await expect(toggle).toBeVisible({ timeout: 8000 })

    await toggle.click()
    await expect(page.getByTestId('expanded-analysis')).toBeVisible()

    await toggle.click()
    await expect(page.getByTestId('expanded-analysis')).toHaveCount(0)
  })

  test('each card state is independent (US2 AS4)', async ({ page }) => {
    await runAnalysis(page, 'mixed-5-games')
    await expect(page.getByTestId('game-row__toggle').first()).toBeVisible({ timeout: 8000 })

    const toggles = page.getByTestId('game-row__toggle')
    const count = await toggles.count()
    expect(count).toBeGreaterThanOrEqual(2)

    await toggles.nth(0).click()
    await toggles.nth(1).click()

    // Both expanded — count of expanded-analysis sections must equal 2.
    await expect(page.getByTestId('expanded-analysis')).toHaveCount(2)
  })

  test('expanded card renders per-game reasoning summary', async ({ page }) => {
    await runAnalysis(page, 'suspect-1-game')
    await expect(page.getByTestId('game-row__toggle').first()).toBeVisible({ timeout: 8000 })

    await page.getByTestId('game-row__toggle').first().click()

    const summary = page.getByTestId('score-summary')
    await expect(summary).toBeVisible()
    await expect(page.getByTestId('score-summary__headline')).not.toBeEmpty()
    // The suspect-1-game fixture scores 0.92 (HIGH). Intro must quote the
    // numeric score so the reader sees the actual value being explained.
    await expect(page.getByTestId('score-summary__intro')).toContainText('92.0%')
    await expect(page.getByTestId('score-summary__intro')).toContainText('ALTO')
  })

  test('unknown signal falls back gracefully (US2 AS5)', async ({ page }) => {
    // Inject a fixture-like response with an unknown signal name via route override.
    await page.route('**/api/analyze**', async (route) => {
      const body =
        'data: {"idx": 0, "status": "done", "score": 0.81, "risk_level": "high", "confidence_interval": [0.75, 0.88], "dominant_signals": ["totally-unknown-signal"], "headers": {"White": "alice123", "Black": "bob456", "Result": "1-0"}, "ply_count": 40, "run_id": "run-unk"}\n' +
        'data: {"done": true}\n'
      await route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body,
      })
    })
    await page.goto('/')
    await page.getByPlaceholder('Nome de usuário...').fill('alice123')
    await page.getByRole('button', { name: /^Analisar$/i }).click()

    await expect(page.getByTestId('game-row__toggle').first()).toBeVisible({ timeout: 8000 })
    await page.getByTestId('game-row__toggle').first().click()

    await expect(page.getByTestId('expanded-analysis')).toBeVisible()
    await expect(page.getByText('Sinal técnico')).toBeVisible()
  })
})
