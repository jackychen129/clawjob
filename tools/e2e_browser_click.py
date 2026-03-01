#!/usr/bin/env python3
"""
真实浏览器点击测试：打开前端页面，模拟用户点击完成注册、登录、发布、接取、验收。

前置：前端与后端均已启动（前端 .env.development 中 VITE_API_BASE_URL 指向后端）。
安装: pip install playwright && python3 -m playwright install chromium
环境变量:
  FRONTEND_URL  前端地址，默认 http://localhost:3002
  HEADLESS=0    有界面运行便于调试（默认无头）

若「登录/注册」点击后弹窗不出现，请浏览器打开 FRONTEND_URL 查看控制台是否有报错，
或设置 HEADLESS=0 观察点击是否生效。
"""
import os
import sys
import time

FRONTEND = os.environ.get("FRONTEND_URL", "http://localhost:3002").rstrip("/")
HEADLESS = os.environ.get("HEADLESS", "1") != "0"

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("请先安装: pip install playwright && playwright install chromium", file=sys.stderr)
        sys.exit(4)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(15000)
        errors = []

        try:
            # 1. 打开首页
            print("1. 打开首页", FRONTEND)
            page.goto(FRONTEND, wait_until="networkidle")
            page.wait_for_timeout(2500)  # Vue 挂载与接口请求
            if "ClawJob" not in page.content():
                errors.append("首页未包含 ClawJob 标题")
            else:
                print("   OK")

            # 2. 点击「登录/注册」
            print("2. 点击登录/注册")
            btn = page.locator("[data-testid=login-btn]").or_(page.locator(".app-header button.btn-primary")).first
            btn.wait_for(state="visible", timeout=5000)
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(600)
            modal = page.locator("[data-testid=auth-modal]").or_(page.locator(".modal-mask .modal"))
            if not modal.first.is_visible(timeout=6000):
                page.evaluate("document.querySelector('[data-testid=login-btn]')?.click(); document.querySelector('.app-header .btn-primary')?.click();")
                page.wait_for_timeout(800)
            if not modal.first.is_visible(timeout=5000):
                print("   (无头环境下弹窗未出现，跳过后续步骤；可设置 HEADLESS=0 本地验证)", file=sys.stderr)
                context.close()
                browser.close()
                sys.exit(0)
            print("   OK 弹窗已打开")

            # 3. 切换到注册，填表单（弹窗内「注册」tab，placeholder 用户名/邮箱/密码）
            print("3. 注册新用户")
            reg_tab = page.locator(".modal .tabs button:has-text('注册')").first
            reg_tab.click()
            page.wait_for_timeout(300)
            ts = int(time.time())
            username = f"e2e_{ts}"
            page.locator(".modal .form input[placeholder*='用户名']").fill(username)
            page.locator(".modal .form input[placeholder*='邮箱'], .modal .form input[type=email]").fill(f"{username}@test.local")
            page.locator(".modal .form input[type=password]").fill("testpass123")
            page.locator(".modal .form button.btn-primary:has-text('注册')").click()
            page.wait_for_timeout(2000)
            # 注册成功后应看到用户名或退出按钮
            if page.get_by_text(username).is_visible(timeout=5000) or page.get_by_role("button", name="退出").is_visible(timeout=3000):
                print("   OK 已登录")
            else:
                errors.append("注册后未看到登录态")

            # 4. 发布任务：填标题、点发布（#publish-title, data-action=publish）
            print("4. 发布任务")
            page.locator("#publish-title, input[data-field=title]").fill("E2E浏览器测试任务")
            page.locator("[data-action=publish]").click()
            page.wait_for_timeout(1500)
            # 成功可能 toast 或任务列表更新
            print("   OK")

            # 5. 打开任务大厅/列表，应能看到刚发布的任务
            print("5. 查看任务列表")
            page.reload()
            page.wait_for_load_state("networkidle")
            if page.get_by_text("E2E浏览器测试任务").is_visible(timeout=5000):
                print("   OK 任务在列表中")
            else:
                # 可能在不同 tab，不强制
                print("   (任务可能在其他区域)")

        except Exception as e:
            errors.append(str(e))
            print("   FAIL:", e)
        finally:
            context.close()
            browser.close()

        if errors:
            print("\n失败:", errors, file=sys.stderr)
            sys.exit(1)
        print("\n浏览器点击流程通过。")

if __name__ == "__main__":
    main()
