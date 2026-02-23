#!/usr/bin/env python3
"""
模拟浏览器操作顺序：按前端实际调用的 API 顺序执行，覆盖所有主要功能。
用法: CLAWJOB_API_URL=http://localhost:8002 python3 tools/browser_flow_test.py
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
    ts = int(time.time())
    user1, user2 = f"flow_u1_{ts}", f"flow_u2_{ts}"
    password = "pass123"
    errors = []

    # 1. 任务大厅（未登录，首页会调）
    print("1. GET /tasks (任务大厅)")
    try:
        code, data = req("GET", "/tasks?limit=5")
        assert code == 200 and "tasks" in data
        print("   OK, tasks count:", len(data.get("tasks", [])))
    except Exception as e:
        errors.append(f"GET /tasks: {e}")
        print("   FAIL:", e)

    # 2. 注册用户 A（点击注册）
    print("2. POST /auth/register (用户A)")
    try:
        code, data = req("POST", "/auth/register", {"username": user1, "email": f"{user1}@test.local", "password": password})
        assert code == 200 and "access_token" in data
        token_a = data["access_token"]
        print("   OK, token obtained")
    except Exception as e:
        errors.append(f"register A: {e}")
        print("   FAIL:", e)
        sys.exit(2)

    # 3. 登录态：获取当前用户（前端 getAccountMe）
    print("3. GET /account/me (我的信息)")
    try:
        code, data = req("GET", "/account/me", token=token_a)
        assert code == 200 and "user_id" in data and "credits" in data
        print("   OK, credits:", data.get("credits"))
    except Exception as e:
        errors.append(f"GET /account/me: {e}")
        print("   FAIL:", e)

    # 4. 流水（前端账户弹窗可能调）
    print("4. GET /account/transactions")
    try:
        code, data = req("GET", "/account/transactions?limit=5", token=token_a)
        assert code == 200 and "transactions" in data
        print("   OK")
    except Exception as e:
        errors.append(f"GET /account/transactions: {e}")
        print("   FAIL:", e)

    # 5. 充值（发布带奖励任务前）
    print("5. POST /account/recharge")
    try:
        code, data = req("POST", "/account/recharge", {"amount": 30}, token=token_a)
        assert code == 200 and data.get("credits", 0) >= 30
        print("   OK, credits:", data.get("credits"))
    except Exception as e:
        errors.append(f"POST /account/recharge: {e}")
        print("   FAIL:", e)

    # 5b. 充值订单（信用卡/支付宝/比特币渠道）
    print("5b. POST /account/recharge/orders + /recharge/confirm (支付渠道充值)")
    try:
        code, data = req("POST", "/account/recharge/orders", {"amount": 10, "payment_method_type": "credit_card"}, token=token_a)
        assert code == 200 and data.get("order_id") and data.get("payment_url")
        code2, data2 = req("POST", "/account/recharge/confirm", {"order_id": data["order_id"]}, token=token_a)
        assert code2 == 200 and data2.get("credits", 0) >= 40
        print("   OK, credits after order:", data2.get("credits"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("   (跳过：后端未提供 /account/recharge/orders)")
        else:
            errors.append(f"recharge/orders or confirm: {e}")
            print("   FAIL:", e)
    except Exception as e:
        errors.append(f"recharge/orders or confirm: {e}")
        print("   FAIL:", e)

    # 6. 发布任务（发布表单提交）
    print("6. POST /tasks (发布任务)")
    try:
        code, data = req("POST", "/tasks", {
            "title": "流程测试任务",
            "description": "browser_flow_test",
            "reward_points": 0,
        }, token=token_a)
        assert code == 200 and "id" in data
        task_id = data["id"]
        print("   OK, task_id:", task_id)
    except Exception as e:
        errors.append(f"POST /tasks: {e}")
        print("   FAIL:", e)
        sys.exit(2)

    # 7. 任务详情（点击任务卡片）
    print("7. GET /tasks/{id}")
    try:
        code, data = req("GET", f"/tasks/{task_id}")
        assert code == 200 and data.get("id") == task_id
        print("   OK, status:", data.get("status"))
    except Exception as e:
        errors.append(f"GET /tasks/{{id}}: {e}")
        print("   FAIL:", e)

    # 8. 注册用户 B，并登录
    print("8. POST /auth/register (用户B)")
    try:
        code, data = req("POST", "/auth/register", {"username": user2, "email": f"{user2}@test.local", "password": password})
        assert code == 200
        token_b = data["access_token"]
        print("   OK")
    except Exception as e:
        errors.append(f"register B: {e}")
        print("   FAIL:", e)
        sys.exit(2)

    # 9. 我的 Agent 列表（接取前）
    print("9. GET /agents/mine")
    try:
        code, data = req("GET", "/agents/mine", token=token_b)
        assert code == 200 and "agents" in data
        print("   OK, agents:", len(data.get("agents", [])))
    except Exception as e:
        errors.append(f"GET /agents/mine: {e}")
        print("   FAIL:", e)

    # 10. 注册 Agent（接取任务必须先有 Agent）
    print("10. POST /agents/register")
    try:
        code, data = req("POST", "/agents/register", {"name": "FlowAgent", "description": "test", "agent_type": "general"}, token=token_b)
        assert code == 200 and "id" in data
        agent_id = data["id"]
        print("   OK, agent_id:", agent_id)
    except Exception as e:
        errors.append(f"POST /agents/register: {e}")
        print("   FAIL:", e)
        sys.exit(2)

    # 11. 订阅任务（接取）
    print("11. POST /tasks/{id}/subscribe")
    try:
        code, data = req("POST", f"/tasks/{task_id}/subscribe", {"agent_id": agent_id}, token=token_b)
        assert code == 200
        print("   OK:", data.get("message", ""))
    except Exception as e:
        errors.append(f"POST subscribe: {e}")
        print("   FAIL:", e)

    # 12. 发布者验收（0 奖励直接确认关闭）
    print("12. POST /tasks/{id}/confirm (发布者验收)")
    try:
        code, data = req("POST", f"/tasks/{task_id}/confirm", token=token_a)
        assert code == 200
        print("   OK:", data.get("message", ""))
    except Exception as e:
        errors.append(f"POST confirm: {e}")
        print("   FAIL:", e)

    # 13. 再次查任务状态
    print("13. GET /tasks/{id} (验证 completed)")
    try:
        code, data = req("GET", f"/tasks/{task_id}")
        assert code == 200 and data.get("status") == "completed"
        print("   OK, status:", data.get("status"))
    except Exception as e:
        errors.append(f"GET task status: {e}")
        print("   FAIL:", e)

    # 14. 登录接口（模拟切换账号后登录）
    print("14. POST /auth/login")
    try:
        code, data = req("POST", "/auth/login", {"username": user1, "password": password})
        assert code == 200 and "access_token" in data
        print("   OK")
    except Exception as e:
        errors.append(f"POST /auth/login: {e}")
        print("   FAIL:", e)

    # 15. 余额与支付方式（账户页）
    print("15. GET /account/balance, GET /account/payment-methods")
    try:
        code, bal = req("GET", "/account/balance", token=token_a)
        assert code == 200
        code2, pm = req("GET", "/account/payment-methods", token=token_a)
        assert code2 == 200 and "payment_methods" in pm
        print("   OK, balance:", bal.get("credits"))
    except Exception as e:
        errors.append(f"balance/payment-methods: {e}")
        print("   FAIL:", e)

    print("")
    if errors:
        print("存在失败项:", errors, file=sys.stderr)
        sys.exit(1)
    print("全部功能点通过（与浏览器操作顺序一致）。")

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
