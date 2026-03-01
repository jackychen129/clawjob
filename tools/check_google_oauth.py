#!/usr/bin/env python3
"""
检查 Google OAuth 配置是否就绪。
用法：
  python3 tools/check_google_oauth.py
  # 或指定后端地址
  CLAWJOB_API_URL=https://api.xxx.com python3 tools/check_google_oauth.py
"""
import os
import sys

try:
    import urllib.request
    import json
except Exception:
    pass

API_BASE = os.environ.get("CLAWJOB_API_URL", "http://localhost:8000").rstrip("/")
STATUS_URL = f"{API_BASE}/auth/google/status"


def main():
    print("ClawJob Google OAuth 配置检查")
    print("=" * 50)
    print(f"后端 API: {API_BASE}")
    print(f"请求:     GET {STATUS_URL}")
    print()

    try:
        req = urllib.request.Request(STATUS_URL)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[失败] HTTP {e.code}: {e.reason}")
        if e.code == 404:
            print("  提示: 请确认后端已启动且路由包含 /auth/google/status")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"[失败] 无法连接: {e.reason}")
        print("  提示: 请确认后端已启动，或设置 CLAWJOB_API_URL 为正确地址")
        sys.exit(1)
    except Exception as e:
        print(f"[失败] {e}")
        sys.exit(1)

    configured = data.get("configured", False)
    redirect_uri = data.get("redirect_uri", "")
    frontend_url = data.get("frontend_url", "")
    hint = data.get("hint", "")

    print("[后端环境变量]")
    print(f"  configured:   {configured}")
    print(f"  redirect_uri: {redirect_uri}")
    print(f"  frontend_url: {frontend_url}")
    print()
    if hint:
        print(f"  说明: {hint}")
        print()

    if not configured:
        print("[结论] Google 登录未配置或未生效")
        print()
        print("请在后端环境中设置：")
        print("  GOOGLE_CLIENT_ID=     （从 Google Cloud Console 复制）")
        print("  GOOGLE_CLIENT_SECRET= （从 Google Cloud Console 复制）")
        print("  GOOGLE_REDIRECT_URI=  （必须与下方「Google Console」中完全一致）")
        print("  FRONTEND_URL=         （前端 SPA 完整地址，登录成功后跳转到这里）")
        print()
        print("Google Cloud Console 检查：")
        print("  1. APIs 与服务 → 凭据 → 创建 OAuth 2.0 客户端 ID → 类型「Web 应用」")
        print(f"  2. 「已授权的重定向 URI」中必须有一项与下面完全一致（一字不差）：")
        print(f"     {redirect_uri or '(未设置 GOOGLE_REDIRECT_URI)'}")
        print("  3. 若前端与 API 不同域，在「已授权的 JavaScript 来源」中添加前端的 origin")
        sys.exit(1)

    print("[结论] 后端已配置 Google OAuth")
    print()
    print("Google Cloud Console 请确认：")
    print(f"  • 「已授权的重定向 URI」包含且仅与该值一致: {redirect_uri}")
    print(f"  • 登录成功后会重定向到: {frontend_url}#/auth/callback?token=...")
    print("  • 若仍无法登录，请检查浏览器地址栏回调 URL 与 FRONTEND_URL 是否一致（含端口/路径）")
    print()
    print("前端请确认：")
    print("  • VITE_API_BASE_URL 或请求的 API 地址指向上述后端")
    print("  • 点击「使用 Google 登录」后应跳转 Google → 授权 → 回到前端并已登录")
    sys.exit(0)


if __name__ == "__main__":
    main()
