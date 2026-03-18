#!/usr/bin/env python3
"""部署后校验：确认线上前端加载的 CSS 包含 runpod-theme 设计系统样式。
用法:
  CLAWJOB_FRONTEND_URL=http://服务器IP:3000 python3 deploy/verify-frontend-styles.py
  或: python3 deploy/verify-frontend-styles.py https://app.example.com
"""
import os
import re
import sys

try:
    import urllib.request
    import urllib.error
    import ssl
except ImportError:
    print("需要 Python 3")
    sys.exit(1)

BASE = (os.environ.get("CLAWJOB_FRONTEND_URL") or (sys.argv[1] if len(sys.argv) > 1 else "")).rstrip("/")
if not BASE:
    print("用法: CLAWJOB_FRONTEND_URL=http://IP:3000 python3 deploy/verify-frontend-styles.py")
    print("  或: python3 deploy/verify-frontend-styles.py https://app.example.com")
    sys.exit(1)

SSL_CTX = ssl.create_default_context()

# 至少出现其一即认为 runpod-theme 已打入构建
THEME_MARKERS = [".page-title", "font-section-title", ".section-desc", ".empty-state", "--font-page-title"]


def main():
    errors = []
    # 1. 拉取 index.html
    try:
        req = urllib.request.Request(f"{BASE}/", headers={"Accept": "text/html"})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as res:
            html = res.read().decode()
    except Exception as e:
        print(f"[FAIL] 无法拉取前端首页: {e}")
        sys.exit(1)

    # 2. 解析主样式表 href（Vite 构建产物 /assets/index-xxx.css）
    m = re.search(r'<link\s+rel=["\']stylesheet["\']\s+[^>]*href=["\']([^"\']+\.css)["\']', html)
    if not m:
        # 兼容无 crossorigin 等写法
        m = re.search(r'href=["\'](/assets/[^"\']+\.css)["\']', html)
    if not m:
        print("[FAIL] index.html 中未找到主样式表 link")
        sys.exit(1)

    css_href = m.group(1)
    if css_href.startswith("/"):
        css_url = f"{BASE.rstrip('/')}{css_href}"
    else:
        css_url = css_href

    # 3. 拉取 CSS
    try:
        req = urllib.request.Request(css_url, headers={"Accept": "text/css"})
        with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as res:
            css = res.read().decode()
    except Exception as e:
        print(f"[FAIL] 无法拉取样式表 {css_url}: {e}")
        sys.exit(1)

    # 4. 检查是否包含主题标记
    found = [marker for marker in THEME_MARKERS if marker in css]
    if not found:
        print("[FAIL] 样式表中未发现 runpod-theme 标记（.page-title / font-section-title / .section-desc 等）")
        print("       可能原因：构建未包含 frontend/src/styles/runpod-theme.css 或部署了旧构建。")
        sys.exit(1)

    print(f"[OK] 前端样式已正确应用（检测到: {', '.join(found[:3])} 等）")
    print(f"     首页: {BASE}/  样式表: {css_url}")
    sys.exit(0)


if __name__ == "__main__":
    main()
