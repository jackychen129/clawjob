import { test, expect } from '@playwright/test'

test.describe('站点冒烟', () => {
  test('首页可加载且标题含 ClawJob', async ({ page }) => {
    await page.goto('/', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page).toHaveTitle(/ClawJob/i)
    await expect(page.locator('#app, #main-content, iframe[src*="/home/"]').first()).toBeAttached({ timeout: 30000 })
  })

  test('Hash 路由任务页可打开（公开大厅）', async ({ page }) => {
    await page.goto('/#/tasks', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page.locator('body')).toBeVisible()
  })

  test('社区页可打开且布局可见', async ({ page }) => {
    await page.goto('/#/community', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page.locator('.community-view')).toBeVisible({ timeout: 30000 })
    await expect(page.locator('.community-layout')).toBeVisible()
  })

  test('Forum 重定向到 tasks', async ({ page }) => {
    await page.goto('/#/forum', { waitUntil: 'domcontentloaded', timeout: 60000 })
    await expect(page).toHaveURL(/#\/tasks/, { timeout: 30000 })
  })

  test('tasks pulse 深链可打开并保留 query', async ({ page }) => {
    await page.goto('/#/tasks?pulse=verify')
    await expect(page.locator('body')).toBeVisible()
    await expect(page).toHaveURL(/pulse=verify/)
  })

  test('tasks taskId 深链保留 query', async ({ page }) => {
    await page.goto('/#/tasks?taskId=1')
    await expect(page).toHaveURL(/taskId=1/)
  })

  test('Admin 任务链接 query 名 taskId', async ({ page }) => {
    await page.goto('/#/admin/disputes')
    await expect(page.locator('body')).toBeVisible()
  })

  test('落地页 home 静态资源可访问', async ({ page }) => {
    const res = await page.request.get('/home/index.html')
    expect(res.ok()).toBeTruthy()
  })

  test('根域 sitemap 可访问', async ({ page }) => {
    const res = await page.request.get('/sitemap.xml')
    expect(res.ok()).toBeTruthy()
    const body = await res.text()
    expect(body).toContain('clawjob.com.cn/#/tasks')
  })
})
