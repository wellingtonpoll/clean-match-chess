// Feature 006 / T024 — Playwright cross-viewport E2E config.
//
// Spec: specs/006-frontend-ux-improvements/contracts/playwright_e2e.contract.md.
// Viewport matrix per FR-012; webServer per FR-014 / US4 AS5.
//
// Default browser: Chromium for all projects (mobile viewports use Chromium
// with iPhone viewport overrides). Set PLAYWRIGHT_BROWSER=webkit in CI (with
// `npx playwright install --with-deps webkit`) to exercise Safari rendering.

import { defineConfig, devices } from '@playwright/test'

const useWebKit = process.env.PLAYWRIGHT_BROWSER === 'webkit'

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  expect: { timeout: 5_000 },
  reporter: [
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'mobile-iphone-se',
      use: useWebKit
        ? { ...devices['iPhone SE'] }
        : {
            ...devices['Desktop Chrome'],
            viewport: { width: 375, height: 667 },
            isMobile: false,
            hasTouch: true,
          },
    },
    {
      name: 'mobile-iphone-11-pro-max',
      use: useWebKit
        ? { ...devices['iPhone 11 Pro Max'] }
        : {
            ...devices['Desktop Chrome'],
            viewport: { width: 414, height: 896 },
            isMobile: false,
            hasTouch: true,
          },
    },
    {
      name: 'desktop-1280',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: 'desktop-1920',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1920, height: 1080 },
      },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
