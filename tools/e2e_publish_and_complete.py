#!/usr/bin/env python3
"""
ClawJob 端到端流程：用真实数据模拟用户 + OpenClaw 发布任务并完成任务。
用法（后端需已启动，且数据库已迁移）:
  export CLAWJOB_API_URL=http://localhost:8000   # 若 8000 被占用可改为 8001
  python3 e2e_publish_and_complete.py

注意：必须使用本仓库的 ClawJob 后端（health 返回 service=clawjob-backend），
否则 /auth/register 可能 404；若 8000 上运行的是其他服务，可另起 ClawJob 于 8001。

流程：
  1. 发布者注册/登录 -> 充值 -> 发布一条无奖励任务
  2. 接取者注册/登录 -> 注册 Agent -> 接取该任务
  3. 接取者提交完成 -> 发布者验收（或 0 奖励任务直接关闭）
"""
import os
import sys
import json
import time
import urllib.request
import urllib.error

API = os.environ.get("CLAWJOB_API_URL", "http://localhost:8000").rstrip("/")

def req(method: str, path: str, body: dict = None, token: str = None):
    url = f"{API}{path}"
    data = json.dumps(body).encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req_obj = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req_obj, timeout=15) as r:
        return r.getcode(), json.loads(r.read().decode("utf-8"))

def main():
    print("检查后端:", API)
    try:
        req_obj = urllib.request.Request(f"{API}/health", method="GET")
        with urllib.request.urlopen(req_obj, timeout=5) as r:
            health = json.loads(r.read().decode("utf-8"))
        if health.get("status") != "healthy":
            print("后端未就绪:", health, file=sys.stderr)
            sys.exit(4)
    except urllib.error.URLError as e:
        print("无法连接后端，请先启动: cd backend && PYTHONPATH=. python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000", file=sys.stderr)
        print("错误:", e, file=sys.stderr)
        sys.exit(4)
    except Exception as e:
        print("健康检查失败:", e, file=sys.stderr)
        sys.exit(4)

    # 探测 auth 路由是否存在（GET 会返回 405，若 404 说明未挂载 auth）
    try:
        probe = urllib.request.Request(f"{API}/auth/register", method="GET")
        urllib.request.urlopen(probe, timeout=3)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("错误: /auth/register 返回 404，请确认当前运行的是 ClawJob 后端（clawjob/backend）且已包含 auth 路由。", file=sys.stderr)
            sys.exit(5)
    except Exception:
        pass

    ts = int(time.time())
    publisher_user = f"publisher_{ts}"
    executor_user = f"executor_{ts}"
    password = "testpass123"
    print("1. 发布者注册:", publisher_user)
    _, reg = req("POST", "/auth/register", {
        "username": publisher_user,
        "email": f"{publisher_user}@test.local",
        "password": password,
    })
    pub_token = reg["access_token"]
    pub_uid = reg.get("user_id")
    print("   获得 token, user_id:", pub_uid)

    print("2. 接取者注册:", executor_user)
    _, reg2 = req("POST", "/auth/register", {
        "username": executor_user,
        "email": f"{executor_user}@test.local",
        "password": password,
    })
    exe_token = reg2["access_token"]
    print("   获得 token")

    print("3. 发布者充值 50 点")
    _, bal = req("POST", "/account/recharge", {"amount": 50}, pub_token)
    print("   当前余额:", bal.get("credits"))

    print("4. 发布者发布任务（无奖励，无需 webhook）")
    _, task_res = req("POST", "/tasks", {
        "title": "E2E 测试任务：整理需求列表",
        "description": "由 e2e_publish_and_complete.py 自动创建，模拟 OpenClaw 发布",
        "reward_points": 0,
    }, pub_token)
    task_id = task_res["id"]
    print("   任务 ID:", task_id)

    print("5. 接取者注册 Agent")
    _, agent_res = req("POST", "/agents/register", {
        "name": "E2E-Agent",
        "description": "端到端测试用 Agent",
        "agent_type": "general",
    }, exe_token)
    agent_id = agent_res["id"]
    print("   Agent ID:", agent_id)

    print("6. 接取者订阅/接取任务")
    _, sub = req("POST", f"/tasks/{task_id}/subscribe", {"agent_id": agent_id}, exe_token)
    print("   ", sub.get("message", sub))

    print("7. 发布者关闭任务（0 奖励任务可直接确认关闭）")
    _, conf = req("POST", f"/tasks/{task_id}/confirm", {}, pub_token)
    print("   ", conf.get("message", conf))

    print("8. 验证任务状态为 completed")
    _, task_get = req("GET", f"/tasks/{task_id}")
    status = task_get.get("status")
    print("   任务状态:", status)
    if status != "completed":
        print("   预期 completed，失败", file=sys.stderr)
        sys.exit(1)
    print("")
    print("E2E 通过：发布 -> 接取 -> 关闭任务 流程完成。")

if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        print(f"HTTP {e.code}: {body}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(3)
