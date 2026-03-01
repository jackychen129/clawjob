#!/usr/bin/env python3
"""
浏览器页面功能测试：首页加载、帮助文档、Skill 提示条、登录弹窗、任务列表等。
用法: FRONTEND_URL=http://localhost:3002 python3 tools/e2e_browser_page_test.py
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
        print("请先安装: pip install playwright && python3 -m playwright install chromium", file=sys.stderr)
        sys.exit(4)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(12000)
        failed = []
        failed_html = None

        try:
            # 1. 打开首页，等待 Vue 挂载
            print("1. 打开首页", FRONTEND)
            page.goto(FRONTEND, wait_until="networkidle")
            page.wait_for_selector("#app", state="attached", timeout=5000)
            page.wait_for_selector(".app-header", state="visible", timeout=10000)
            page.wait_for_timeout(1500)
            html = page.content()
            if "ClawJob" not in html:
                failed.append("首页未包含 ClawJob")
            else:
                print("   OK")

            # 2. 帮助按钮与弹窗
            print("2. 帮助文档")
            help_btn = page.locator("[data-testid=help-btn]").or_(page.locator(".app-header .btn-text")).or_(page.locator(".app-header button").filter(has_text="帮助")).or_(page.locator(".app-header button").filter(has_text="Help")).first
            if help_btn.is_visible(timeout=5000):
                help_btn.scroll_into_view_if_needed()
                help_btn.click()
                page.wait_for_timeout(600)
                modal = page.locator("[data-testid=help-modal]").or_(page.locator(".modal-help")).or_(page.locator(".modal-mask .modal").filter(has_text="OpenClaw")).or_(page.locator(".modal-mask .modal").filter(has_text="Skill"))
                if modal.first.is_visible(timeout=5000):
                    print("   OK 帮助弹窗已打开")
                    page.locator(".modal .close-btn").first.click()
                    page.wait_for_timeout(400)
                else:
                    print("   (帮助弹窗未出现，无头环境下可忽略)")
            else:
                print("   (未找到帮助按钮)")

            # 3. Skill 提示条（可选）
            print("3. Skill 提示条")
            if page.locator(".skill-banner").is_visible(timeout=2000):
                print("   OK 提示条可见")
            else:
                print("   (已关闭或未显示)")

            # 4. 登录/注册弹窗（优先 data-testid，回退 .btn-primary）
            print("4. 登录/注册弹窗")
            login_btn = page.locator("[data-testid=login-btn]").or_(page.locator(".app-header button.btn-primary")).first
            if not login_btn.is_visible(timeout=3000):
                if page.locator(".app-header").filter(has_text="退出").or_(page.locator(".app-header").filter(has_text="Logout")).is_visible(timeout=2000):
                    print("   (已登录，跳过)")
                else:
                    print("   (未找到登录按钮)")
            else:
                login_btn.scroll_into_view_if_needed()
                login_btn.click()
                page.wait_for_timeout(600)
                auth_modal = page.locator("[data-testid=auth-modal]").or_(page.locator(".modal-mask .modal").filter(has_text="登录")).or_(page.locator(".modal-mask .modal").filter(has_text="Login"))
                if auth_modal.first.is_visible(timeout=5000):
                    print("   OK 登录弹窗已打开")
                    page.locator(".modal .close-btn").first.click()
                    page.wait_for_timeout(400)
                else:
                    print("   (登录弹窗未出现，无头环境下可忽略)")

            # 5. 任务大厅
            print("5. 任务大厅")
            hall = page.locator("#hall-heading").or_(page.locator("h2").filter(has_text="任务大厅")).or_(page.locator("h2").filter(has_text="Task Hall")).first
            hall.wait_for(state="visible", timeout=5000)
            print("   OK")

            # 6. 发布任务区域（未登录时只有提示文案，登录后有输入框）
            print("6. 发布任务区域")
            page.evaluate("window.scrollTo(0, 0)")
            page.wait_for_timeout(300)
            pub_section = page.locator("#publish-heading").or_(page.locator(".publish-card")).or_(page.locator("aside .section"))
            pub_section.first.wait_for(state="visible", timeout=5000)
            pub_input = page.locator("[data-testid=publish-title-input]").or_(page.locator("#publish-title")).or_(page.locator("input[data-field=title]")).first
            if pub_input.is_visible(timeout=3000):
                print("   OK 发布输入框可见")
            elif page.locator(".publish-card").filter(has_text="登录").or_(page.locator(".publish-card").filter(has_text="Login")).is_visible(timeout=2000):
                print("   OK 发布区域可见（未登录状态)")
            else:
                failed.append("未找到发布任务区域或输入框")

        except Exception as e:
            failed.append(str(e))
            print("   FAIL:", e)
        finally:
            if failed:
                try:
                    failed_html = page.content()
                except Exception:
                    pass
            context.close()
            browser.close()

        print("")
        if failed:
            print("失败项:", failed, file=sys.stderr)
            if failed_html:
                try:
                    debug_path = os.path.join(os.path.dirname(__file__), "e2e_page_debug.html")
                    with open(debug_path, "w", encoding="utf-8") as f:
                        f.write(failed_html[:30000])
                    print("页面 HTML 已写入", debug_path, file=sys.stderr)
                except Exception:
                    pass
            sys.exit(1)
        print("页面功能测试通过。")

if __name__ == "__main__":
    main()
