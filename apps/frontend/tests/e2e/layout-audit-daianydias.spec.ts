// Layout audit spec — user-requested visual probe with username "daianydias".
//
// Goal (from user 2026-05-25): use Playwright to surface components that
// ignore viewport width or wrap improperly, breaking the page layout.
// Runs against every viewport project; captures screenshots into
// `playwright-report/` and emits per-viewport measurements as console output
// (visible in --reporter=list runs) so misalignments can be reviewed
// without needing eyes on the running browser.

import { test, expect, type Page } from '@playwright/test'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { mockStream } from './mock-stream'

// HTML reporter cleans `playwright-report/` between runs, so we write our
// screenshots to a sibling dir that survives runs.
const SCREENSHOT_DIR = join(__dirname, '__layout_audit__')
mkdirSync(SCREENSHOT_DIR, { recursive: true })

interface Measurement {
  viewport: string
  stage: string
  documentScrollWidth: number
  documentClientWidth: number
  overflowDeltaPx: number
  bodyScrollWidth: number
  headerHeight: number
  headerBrandWrapped: boolean
  searchInputWidth: number
  searchSubmitVisible: boolean
  gameRowOverflowCount: number
  offenders: string[]
}

async function measure(page: Page, viewport: string, stage: string): Promise<Measurement> {
  return page.evaluate(
    ({ vp, st }) => {
      const docEl = document.documentElement
      const body = document.body
      const header = document.querySelector('[data-testid="header"]') as HTMLElement | null
      const brandBtn = document.querySelector('[data-testid="header-brand"]') as HTMLElement | null
      const searchInput = document.querySelector('[data-testid="header-search-input"]') as HTMLElement | null
      const submit = document.querySelector('[data-testid="header-search-submit"]') as HTMLElement | null

      const overflow = docEl.scrollWidth - docEl.clientWidth

      // Brand wrap detection — does the rendered brand button height exceed
      // a single line height? Tag is 9px JetBrains Mono w/ baseline alignment.
      const brandRect = brandBtn?.getBoundingClientRect()
      const brandWrapped = (brandRect?.height ?? 0) > 30 // single line ~22-26px

      // Search submit visibility — is the Analisar button still inside the
      // viewport horizontally?
      const submitRect = submit?.getBoundingClientRect()
      const submitVisible =
        !!submitRect &&
        submitRect.right <= docEl.clientWidth + 1 &&
        submitRect.left >= -1 &&
        submitRect.width > 0

      // Game-row overflow: any row whose scrollWidth > clientWidth
      // is forcing horizontal scroll on a narrow viewport.
      const offenders: string[] = []
      let rowOverflowCount = 0
      document.querySelectorAll('[data-testid="game-row"]').forEach((el, i) => {
        const e = el as HTMLElement
        if (e.scrollWidth > e.clientWidth + 2) {
          rowOverflowCount += 1
          offenders.push(`game-row#${i} scrollW=${e.scrollWidth} clientW=${e.clientWidth}`)
        }
      })

      // Scan every element for outright horizontal overflow vs viewport.
      document.querySelectorAll('*').forEach((el) => {
        const e = el as HTMLElement
        if (!e.offsetParent && e.tagName !== 'BODY' && e.tagName !== 'HTML') return
        const r = e.getBoundingClientRect()
        if (r.right > docEl.clientWidth + 2 && r.width > 0 && r.width < docEl.clientWidth * 1.5) {
          const tag = `${e.tagName.toLowerCase()}[testid=${e.getAttribute('data-testid') ?? '-'}]`
          if (!offenders.find((o) => o.startsWith(tag))) {
            offenders.push(`${tag} right=${r.right.toFixed(0)} (viewport=${docEl.clientWidth})`)
          }
        }
      })

      return {
        viewport: vp,
        stage: st,
        documentScrollWidth: docEl.scrollWidth,
        documentClientWidth: docEl.clientWidth,
        overflowDeltaPx: overflow,
        bodyScrollWidth: body.scrollWidth,
        headerHeight: header?.getBoundingClientRect().height ?? 0,
        headerBrandWrapped: brandWrapped,
        searchInputWidth: searchInput?.getBoundingClientRect().width ?? 0,
        searchSubmitVisible: submitVisible,
        gameRowOverflowCount: rowOverflowCount,
        offenders: offenders.slice(0, 8),
      }
    },
    { vp: viewport, st: stage }
  )
}

async function snapshot(page: Page, viewport: string, stage: string): Promise<void> {
  const filename = `${viewport}__${stage}.png`
  await page.screenshot({ path: join(SCREENSHOT_DIR, filename), fullPage: true })
}

test.describe('Layout audit — daianydias across viewports', () => {
  test('full-flow probe with username daianydias', async ({ page }, info) => {
    const viewport = info.project.name
    const findings: Measurement[] = []

    // Pipe console errors so JS-level overflow / wrap errors surface in report.
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') consoleErrors.push(msg.text())
    })
    page.on('pageerror', (e) => consoleErrors.push(`pageerror: ${e.message}`))

    await mockStream(page, 'mixed-5-games')
    await page.goto('/')

    // Stage 1 — initial hero state.
    await expect(page.getByTestId('hero')).toBeVisible()
    findings.push(await measure(page, viewport, '01-hero'))
    await snapshot(page, viewport, '01-hero')

    // Stage 2 — username typed into header (pre-submit).
    await page.getByTestId('header-search-input').fill('daianydias')
    findings.push(await measure(page, viewport, '02-typed'))
    await snapshot(page, viewport, '02-typed')

    // Stage 3 — submit + wait for results to render.
    await page.getByTestId('header-search-submit').click()
    await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8_000 })
    // Settle: wait for last game in fixture (mixed-5 → 5 rows in `done` state).
    await page.waitForTimeout(500)
    findings.push(await measure(page, viewport, '03-results'))
    await snapshot(page, viewport, '03-results')

    // Stage 4 — expand a card so the expanded "Análise detalhada" section
    // exercises the wider layout.
    const firstToggle = page.getByTestId('game-row__toggle').first()
    await firstToggle.scrollIntoViewIfNeeded()
    await firstToggle.click()
    await page.waitForTimeout(200)
    findings.push(await measure(page, viewport, '04-expanded'))
    await snapshot(page, viewport, '04-expanded')

    // Stage 5 — long-signal-name scenario (regression guard for the
    // `behavioral-patterns/precision-burst` overflow bug reported
    // 2026-05-25 by the maintainer). New page load with a different
    // fixture so the SSE replay swaps cleanly.
    await page.unroute('**/api/analyze**')
    await mockStream(page, 'long-signals')
    await page.getByTestId('header-search-input').fill('daianydias')
    await page.getByTestId('header-search-submit').click()
    await expect(page.getByTestId('game-row').first()).toBeVisible({ timeout: 8_000 })
    await page.waitForTimeout(500)
    findings.push(await measure(page, viewport, '05-long-signals'))
    await snapshot(page, viewport, '05-long-signals')

    // Persist findings into a per-viewport JSON sibling so we can stitch a
    // cross-viewport report after the run.
    const reportPath = join(SCREENSHOT_DIR, `${viewport}.json`)
    writeFileSync(
      reportPath,
      JSON.stringify({ viewport, findings, consoleErrors }, null, 2)
    )

    // Surface a one-line console summary per stage for the list reporter.
    for (const f of findings) {
      // eslint-disable-next-line no-console
      console.log(
        `[${viewport}/${f.stage}] overflow=${f.overflowDeltaPx}px brandWrapped=${f.headerBrandWrapped} submitVisible=${f.searchSubmitVisible} headerH=${f.headerHeight.toFixed(0)} rowOverflows=${f.gameRowOverflowCount} offenders=${f.offenders.length}`
      )
      if (f.offenders.length) {
        // eslint-disable-next-line no-console
        console.log(`  offenders: ${f.offenders.join(' | ')}`)
      }
    }

    // Soft assertion — record but don't fail the test for overflow during
    // the probe. The goal is enumeration, not pass/fail.
    expect.soft(consoleErrors, `console errors: ${consoleErrors.join(' || ')}`).toEqual([])
  })
})
