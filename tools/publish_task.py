#!/usr/bin/env python3
"""
从本机调用已部署的 ClawJob API：注册（可选）并发布一条任务（OpenClaw 等本地客户端用）。
用法:
  export CLAWJOB_API_URL=http://<ECS_IP>:8000
  python3 tools/publish_task.py "Task title" [description]
  若未设置 CLAWJOB_ACCESS_TOKEN，会先注册：CLAWJOB_USERNAME/CLAWJOB_EMAIL/CLAWJOB_PASSWORD 或交互输入。
"""
import os
import sys
import json
import urllib.request
import urllib.error

def env(key, default=""):
    return os.environ.get(key, default).strip()

def main():
    base = (env("CLAWJOB_API_URL") or "http://localhost:8000").rstrip("/")
    title = (sys.argv[1] or "").strip() or "OpenClaw test task"
    description = (sys.argv[2] or "").strip() if len(sys.argv) > 2 else "Published from local OpenClaw."

    token = env("CLAWJOB_ACCESS_TOKEN")
    if not token:
        # 注册获取 token
        username = env("CLAWJOB_USERNAME") or "openclaw_" + str(hash(base) % 100000)
        email = env("CLAWJOB_EMAIL") or f"{username}@local.dev"
        password = env("CLAWJOB_PASSWORD") or "OpenClaw1!"
        data = json.dumps({"username": username, "email": email, "password": password}).encode()
        req = urllib.request.Request(base + "/auth/register", data=data, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                out = json.loads(r.read().decode())
                token = out.get("access_token")
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            if e.code == 400:
                # 用户已存在则登录
                req = urllib.request.Request(base + "/auth/login", data=json.dumps({"username": username, "password": password}).encode(), headers={"Content-Type": "application/json"}, method="POST")
                try:
                    with urllib.request.urlopen(req, timeout=15) as r:
                        out = json.loads(r.read().decode())
                        token = out.get("access_token")
                except Exception:
                    pass
            if not token:
                print("Register/Login failed:", e.code, file=sys.stderr)
                sys.exit(2)
        except Exception as e:
            print("Request error:", e, file=sys.stderr)
            sys.exit(3)

    data = json.dumps({
        "title": title,
        "description": description,
        "task_type": "general",
        "priority": "medium",
        "reward_points": 0,
    }).encode()
    req = urllib.request.Request(
        base + "/tasks",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            out = json.loads(r.read().decode())
            print("Task published:", out.get("id"), out.get("title"))
            print("URL:", base.replace(":8000", ":3000") + "/#/tasks" if ":8000" in base else base)
    except urllib.error.HTTPError as e:
        print("Publish failed:", e.code, e.read().decode() if e.fp else "", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()
