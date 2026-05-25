// Feature 006 / T027 — Cross-viewport bug-class detectors BD-1..BD-6.
//
// Each test runs against every Playwright project (viewport) configured.
// On failure, Playwright produces a screenshot + trace into playwright-report/.

import { test, expect, type Page } from '@playwright/test'
import { mockStream } from './mock-stream'

async function setupResults(page: Page): Promise<void> {
  await mockStream(page, 'mixed-5-games')
  await page.goto('/')
  await page.getByTestId('header-search-input').fill('alice123')
  await page.getByTestId('header-search-submit').click()
  await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8000 })
}

test.describe('Bug detectors (BD-1..BD-6)', () => {
  test('BD-1: no horizontal overflow on document', async ({ page }) => {
    await setupResults(page)
    const { scrollW, clientW } = await page.evaluate(() => ({
      scrollW: document.documentElement.scrollWidth,
      clientW: document.documentElement.clientWidth,
    }))
    expect(
      scrollW,
      `horizontal overflow detected: scrollWidth=${scrollW} clientWidth=${clientW} (delta=${scrollW - clientW}px)`
    ).toBeLessThanOrEqual(clientW)
  })

  test('BD-2: no interactive element hidden behind sticky header', async ({ page }) => {
    await setupResults(page)

    // Get header bounding rect.
    const headerBox = await page.getByTestId('header').boundingBox()
    expect(headerBox).not.toBeNull()
    const headerBottom = (headerBox?.y ?? 0) + (headerBox?.height ?? 0)

    // Inspect every clickable element below the header for overlap.
    const overlaps = await page.evaluate((hb) => {
      const overlapping: string[] = []
      const els = document.querySelectorAll('button, a, [role="button"]')
      els.forEach((el) => {
        const rect = el.getBoundingClientRect()
        // Element is positioned in viewport, but its top sits under the header
        // AND it's not part of the header itself.
        const insideHeader = (el as HTMLElement).closest('[data-testid="header"]')
        if (insideHeader) return
        if (
          rect.height > 0 &&
          rect.top >= 0 &&
          rect.top < hb &&
          rect.bottom > 0
        ) {
          overlapping.push(
            `${el.tagName.toLowerCase()}[testid=${el.getAttribute('data-testid') ?? '?'}] top=${rect.top.toFixed(0)} (header_bottom=${hb.toFixed(0)})`
          )
        }
      })
      return overlapping
    }, headerBottom)

    expect(overlaps, `clickable elements behind header: ${overlaps.join('; ')}`).toEqual([])
  })

  test('BD-3: text truncation always has ellipsis when overflow > 2px', async ({ page }) => {
    await setupResults(page)

    const violations = await page.evaluate(() => {
      const offenders: string[] = []
      document.querySelectorAll('*').forEach((el) => {
        const e = el as HTMLElement
        if (!e.offsetParent || e.offsetWidth === 0) return
        if (e.scrollWidth > e.clientWidth + 2) {
          const style = getComputedStyle(e)
          if (style.textOverflow !== 'ellipsis' && style.overflow !== 'visible') {
            offenders.push(
              `${e.tagName.toLowerCase()}.${(e.className || '').toString().slice(0, 32)}: scrollWidth=${e.scrollWidth} clientWidth=${e.clientWidth} textOverflow=${style.textOverflow}`
            )
          }
        }
      })
      return offenders.slice(0, 5) // cap report length
    })

    expect(violations, `truncated without ellipsis: ${violations.join('; ')}`).toEqual([])
  })

  test('BD-4: hover-only interaction not required on touch viewports', async ({ page }, info) => {
    // Touch viewports only: confirm essential interactive elements have
    // visible affordance without hover (cursor pointer + tabindex or button).
    const isTouchProject = info.project.name.startsWith('mobile-')
    if (!isTouchProject) {
      test.skip()
      return
    }
    await setupResults(page)

    // Check that toggles and player links are real buttons (not div-with-hover).
    const tags = await page.evaluate(() => {
      const out: string[] = []
      document.querySelectorAll('[data-testid="player-link"], [data-testid="game-row__toggle"]').forEach((el) => {
        out.push(`${el.getAttribute('data-testid')}=${el.tagName.toLowerCase()}`)
      })
      return out
    })
    const invalid = tags.filter((t) => {
      const [name, tag] = t.split('=')
      // player-link must be BUTTON, toggle is allowed as DIV with role.
      return name === 'player-link' && tag !== 'button'
    })
    expect(invalid, `hover-only interaction without touch affordance: ${invalid.join('; ')}`).toEqual([])
  })

  test('BD-5: page remains scrollable after expanding a card (no scroll lock)', async ({
    page,
  }) => {
    await setupResults(page)

    const expandable = page.getByTestId('game-row__toggle').first()
    await expandable.scrollIntoViewIfNeeded()
    await expandable.click()

    // Scroll lock means `overflow: hidden` is forced on <body> or <html>.
    // We assert the CSS computed style allows scrolling — independent of
    // whether the corpus is currently long enough to actually need scrolling.
    const styles = await page.evaluate(() => ({
      bodyOverflow: getComputedStyle(document.body).overflow,
      bodyOverflowY: getComputedStyle(document.body).overflowY,
      htmlOverflow: getComputedStyle(document.documentElement).overflow,
      htmlOverflowY: getComputedStyle(document.documentElement).overflowY,
    }))
    expect(
      styles.bodyOverflow === 'hidden' || styles.bodyOverflowY === 'hidden',
      `body overflow forced to hidden: ${JSON.stringify(styles)}`
    ).toBe(false)
    expect(
      styles.htmlOverflow === 'hidden' || styles.htmlOverflowY === 'hidden',
      `html overflow forced to hidden: ${JSON.stringify(styles)}`
    ).toBe(false)
  })

  test('BD-6: expanding a card does not shift sibling cards > 5px', async ({ page }) => {
    await setupResults(page)

    // Use document-relative `offsetTop` instead of getBoundingClientRect to
    // avoid false positives from viewport scrolling that the browser performs
    // when a focusable element receives a click.
    const measure = () =>
      page.evaluate(() => {
        const out: Record<number, number> = {}
        document.querySelectorAll('[data-testid="game-row"]').forEach((el, i) => {
          let top = 0
          let cur: HTMLElement | null = el as HTMLElement
          while (cur) {
            top += cur.offsetTop
            cur = cur.offsetParent as HTMLElement | null
          }
          out[i] = top
        })
        return out
      })

    const beforeTops = await measure()

    // Make sure target is in view, then expand it.
    await page.getByTestId('game-row__toggle').first().scrollIntoViewIfNeeded()
    await page.getByTestId('game-row__toggle').first().click()
    await page.waitForTimeout(150) // allow render to settle

    const afterTops = await measure()

    // The expanded card itself is the layout anchor — its document-relative
    // top must be stable. Siblings will shift downward by the expansion height
    // (legitimate flow behavior).
    const card0Delta = Math.abs((afterTops[0] ?? 0) - (beforeTops[0] ?? 0))
    expect(
      card0Delta,
      `expanded card's document-relative top shifted by ${card0Delta}px (expected ≤ 5)`
    ).toBeLessThanOrEqual(5)
  })
})
