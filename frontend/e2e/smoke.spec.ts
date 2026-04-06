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
})
