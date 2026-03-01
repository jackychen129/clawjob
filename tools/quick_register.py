#!/usr/bin/env python3
"""
ClawJob 快速注册脚本：调用 API 注册用户并输出 token，便于自动化或本地环境配置。
用法:
  export CLAWJOB_API_URL=http://localhost:8000   # 可选，默认 http://localhost:8000
  python3 quick_register.py <username> <email> <password>
  或从环境变量读取: CLAWJOB_USERNAME, CLAWJOB_EMAIL, CLAWJOB_PASSWORD
输出: 打印 access_token、user_id、以及可写入 .env 的片段。
"""
import os
import sys
import json
import urllib.request
import urllib.error

def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()

def main():
    api_base = env("CLAWJOB_API_URL") or "http://localhost:8000"
    base = api_base.rstrip("/")
    register_url = f"{base}/auth/register"

    if len(sys.argv) >= 4:
        username, email, password = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        username = env("CLAWJOB_USERNAME")
        email = env("CLAWJOB_EMAIL")
        password = env("CLAWJOB_PASSWORD")
    if not username or not email or not password:
        print("Usage: quick_register.py <username> <email> <password>", file=sys.stderr)
        print("   or set CLAWJOB_USERNAME, CLAWJOB_EMAIL, CLAWJOB_PASSWORD", file=sys.stderr)
        sys.exit(1)

    data = json.dumps({
        "username": username,
        "email": email,
        "password": password,
    }).encode("utf-8")
    req = urllib.request.Request(
        register_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"Register failed: {e.code} {body}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(3)

    out = json.loads(body)
    token = out.get("access_token")
    user_id = out.get("user_id")
    if not token:
        print("No access_token in response", file=sys.stderr)
        sys.exit(4)

    print("CLAWJOB_ACCESS_TOKEN=" + token)
    if user_id is not None:
        print("CLAWJOB_USER_ID=" + str(user_id))
    print("CLAWJOB_USERNAME=" + username)
    print()
    print("# Add to your .env or shell:")
    print(f"export CLAWJOB_API_URL={api_base}")
    print(f"export CLAWJOB_ACCESS_TOKEN={token}")
    if user_id is not None:
        print(f"export CLAWJOB_USER_ID={user_id}")
    print(f"export CLAWJOB_USERNAME={username}")

if __name__ == "__main__":
    main()
