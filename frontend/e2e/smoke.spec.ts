import { test, expect } from '@playwright/test'

test.describe('站点冒烟', () => {
  test('首页可加载且标题含 ClawJob', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/ClawJob/i)
    await expect(page.locator('body')).toContainText(/ClawJob|Loading/i)
  })

  test('Hash 路由任务页可打开（公开大厅）', async ({ page }) => {
    await page.goto('/#/tasks')
    await expect(page.locator('body')).toBeVisible()
  })

  test('Forum 页面可达', async ({ page }) => {
    await page.goto('/#/forum')
    await expect(page.locator('body')).toBeVisible()
  })

  test('Inbox 页面可达（未登录也应正常渲染）', async ({ page }) => {
    await page.goto('/#/inbox')
    await expect(page.locator('body')).toBeVisible()
  })

  test('tasks pulse 深链可打开并保留 query', async ({ page }) => {
    await page.goto('/#/tasks?pulse=verify')
    await expect(page.locator('body')).toBeVisible()
    await expect(page).toHaveURL(/pulse=verify/)
  })
})
