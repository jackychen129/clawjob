import { defineConfig, devices } from '@playwright/test'

/**
 * 浏览器 E2E：默认对线上站点冒烟（仅加载首页与标题）。
 * 本地：PLAYWRIGHT_BASE_URL=http://localhost:3000 npx playwright test
 */
const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'https://clawjob.com.cn'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: 'list',
  use: {
    baseURL,
    trace: 'on-first-retry',
    ignoreHTTPSErrors: true,
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
