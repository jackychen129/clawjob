"""
ClawJob API 功能测试：认证、任务大厅、发布任务、注册 Agent、订阅任务、账户、验收流程。
"""
import os
import time
from unittest.mock import patch, MagicMock
import pytest
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.database.relational_db import init_db

# NOTE: translated comment in English.
init_db()

# NOTE: translated comment in English.
os.environ["VERIFICATION_CODE_DEV"] = "123456"

client = TestClient(app)

def _unique():
    return str(int(time.time() * 1000))


def _register_user(username: str, email: str, password: str) -> dict:
    """发送验证码后注册，返回 response json（含 access_token）。"""
    r0 = client.post("/auth/send-verification-code", json={"email": email})
    assert r0.status_code == 200, r0.text
    r = client.post(
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "verification_code": os.environ.get("VERIFICATION_CODE_DEV", "123456"),
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_health():
    """健康检查"""
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["service"] == "clawjob-backend"


def test_tasks_list_public():
    """任务大厅：无需登录即可获取任务列表"""
    r = client.get("/tasks")
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    assert "total" in data
    assert isinstance(data["tasks"], list)
    assert isinstance(data["total"], int)


def test_tasks_list_reward_filter_and_sort():
    """任务大厅：奖励区间与排序参数"""
    r = client.get("/tasks", params={"reward_min": 0, "reward_max": 100})
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    for t in data["tasks"]:
        assert t.get("reward_points", 0) >= 0 and t.get("reward_points", 0) <= 100
    r2 = client.get("/tasks", params={"sort": "reward_desc", "limit": 5})
    assert r2.status_code == 200
    r3 = client.get("/tasks", params={"sort": "deadline_asc"})
    assert r3.status_code == 200


def test_stats_public():
    """平台统计：无需登录即可获取"""
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "tasks_total" in data
    assert "tasks_completed" in data
    assert "rewards_paid" in data
    assert "agents_active" in data
    assert isinstance(data["tasks_total"], int)
    assert isinstance(data["tasks_completed"], int)


def test_register_and_login():
    """注册与登录（邮箱+验证码）"""
    u = f"testuser_{_unique()}"
    email = f"{u}@example.com"
    data = _register_user(u, email, "testpass123")
    assert "access_token" in data
    assert data.get("username") == u
    token = data["access_token"]

    # NOTE: translated comment in English.
    r2 = client.post(
        "/auth/login",
        json={"username": u, "password": "testpass123"},
    )
    assert r2.status_code == 200
    assert "access_token" in r2.json()


def test_guest_token():
    """游客 Token：无需注册即可获取 token 并发布任务；响应含 is_guest 与 register_hint"""
    r = client.post("/auth/guest-token")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data.get("is_guest") is True
    assert "register_hint" in data or "register_hint_en" in data
    assert (data.get("username") or "").startswith("guest_")
    token = data["access_token"]
    # NOTE: translated comment in English.
    r2 = client.post(
        "/tasks",
        json={"title": "游客发布测试", "description": "guest token test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200, r2.text
    assert "id" in r2.json()
    # NOTE: translated comment in English.
    r3 = client.get("/account/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    assert r3.json().get("is_guest") is True


def _register_via_skill_second_task_json():
    """模拟 OpenClaw 按 SKILL 模板生成的第二条任务（reward 0，无需 webhook）。"""
    return {
        "title": "【pytest】Skill 注册第二条（由 OpenClaw 侧生成）",
        "description": (
            "Context: 自动化测试模拟 OpenClaw 根据 ClawJob Skill 模板撰写的第二条开放任务。\n\n"
            "Deliverables:\n- 任务可被大厅展示\n- 描述包含必要小节\n\n"
            "Acceptance criteria:\n- 注册接口返回两条 auto_published_tasks\n\n"
            "Constraints:\n- 测试环境无奖励点\n\nTime estimate: 30m"
        ),
        "task_type": "analysis",
        "priority": "medium",
        "reward_points": 0,
        "category": "research",
    }


def test_register_via_skill_auto_tasks_and_bonus():
    """Skill 注册赠送 500 点；握手由平台完成；第二条开放任务由 OpenClaw 生成内容并在同请求内自动发布。"""
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "OpenClaw",
            "description": "from test",
            "agent_type": "general",
            "second_task": _register_via_skill_second_task_json(),
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("username", "").startswith("skill_")
    assert data.get("signup_bonus_credits") == 500
    assert data.get("auto_task_reward_allocated") == 0
    assert data.get("credits") == 500
    tasks = data.get("auto_published_tasks") or []
    assert len(tasks) == 2
    assert tasks[0].get("status") == "completed"
    assert tasks[1].get("status") == "open"
    assert int(tasks[1].get("reward_points") or 0) == 0
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me = client.get("/account/me", headers=headers)
    assert me.status_code == 200
    assert me.json().get("credits") == 500
    created = client.get("/tasks/created-by-me", headers=headers)
    assert created.status_code == 200
    created_tasks = created.json().get("tasks") or []
    ids = {int(t.get("id")) for t in tasks}
    assert ids.issubset({int(t.get("id")) for t in created_tasks})


def test_register_via_skill_second_task_with_reward_deducts_credits():
    """第二条带奖励时需 webhook；从 500 点中扣除奖励点数。"""
    st = _register_via_skill_second_task_json()
    st["reward_points"] = 100
    st["completion_webhook_url"] = "https://example.com/clawjob-webhook"
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "OpenClawReward",
            "description": "reward test",
            "agent_type": "general",
            "second_task": st,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("credits") == 400
    assert data.get("auto_task_reward_allocated") == 100
    tasks = data.get("auto_published_tasks") or []
    assert len(tasks) == 2
    assert int(tasks[1].get("reward_points") or 0) == 100


def test_register_duplicate_username():
    """重复用户名注册应失败"""
    uid = _unique()
    dup_username = f"dupuser_{uid}"
    _register_user(dup_username, f"dup1_{uid}@example.com", "pass")
    r = client.post(
        "/auth/send-verification-code",
        json={"email": f"dup2_{uid}@example.com"},
    )
    assert r.status_code == 200
    r = client.post(
        "/auth/register",
        json={
            "username": dup_username,
            "email": f"dup2_{uid}@example.com",
            "password": "pass",
            "verification_code": os.environ.get("VERIFICATION_CODE_DEV", "123456"),
        },
    )
    assert r.status_code == 400
    assert "用户名" in r.json().get("detail", "")


def test_publish_task_requires_auth():
    """发布任务需要登录"""
    r = client.post(
        "/tasks",
        json={"title": "test", "description": "desc"},
    )
    assert r.status_code == 401


def test_full_flow_register_login_publish_agent_subscribe():
    """完整流程：注册 -> 登录 -> 发布任务 -> 注册 Agent -> 订阅任务"""
    u = f"flowuser_{_unique()}"
    email = f"{u}@example.com"
    # NOTE: translated comment in English.
    data = _register_user(u, email, "flowpass")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # NOTE: translated comment in English.
    r = client.post(
        "/tasks",
        json={"title": "测试任务", "description": "用于 API 测试"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_data = r.json()
    assert "id" in task_data
    task_id = task_data["id"]

    # NOTE: translated comment in English.
    r = client.get("/tasks")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    ids = [t["id"] for t in tasks]
    assert task_id in ids

    # NOTE: translated comment in English.
    r = client.post(
        "/agents/register",
        json={"name": "测试Agent", "description": "测试用"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    agent_data = r.json()
    assert "id" in agent_data
    agent_id = agent_data["id"]

    # NOTE: translated comment in English.
    r = client.get("/agents/mine", headers=headers)
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert len(agents) >= 1
    assert any(a["id"] == agent_id for a in agents)

    # NOTE: translated comment in English.
    r = client.post(
        f"/tasks/{task_id}/subscribe",
        json={"agent_id": agent_id},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert "订阅" in r.json().get("message", "")

    # NOTE: translated comment in English.
    r = client.post(
        f"/tasks/{task_id}/subscribe",
        json={"agent_id": agent_id},
        headers=headers,
    )
    assert r.status_code == 200
    assert "已订阅" in r.json().get("message", "")


def test_candidates_public():
    """GET /candidates 无需登录"""
    r = client.get("/candidates")
    assert r.status_code == 200
    data = r.json()
    assert "candidates" in data
    assert isinstance(data["candidates"], list)


def test_publish_with_invited_agents_and_subscribe():
    """发布任务时指定接取者，仅该 Agent 可订阅"""
    u = f"invuser_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "invpass")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # NOTE: translated comment in English.
    r = client.post("/agents/register", json={"name": "PubAgent", "description": "pub"}, headers=headers)
    assert r.status_code == 200
    pub_agent_id = r.json()["id"]
    # NOTE: translated comment in English.
    r = client.post(
        "/tasks",
        json={"title": "仅指定接取", "description": "测试", "invited_agent_ids": [pub_agent_id]},
        headers=headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]
    # NOTE: translated comment in English.
    u2 = f"invuser2_{_unique()}"
    data2 = _register_user(u2, f"{u2}@example.com", "invpass")
    token2 = data2["access_token"]
    r = client.post("/agents/register", json={"name": "OtherAgent", "description": "other"}, headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 200
    other_agent_id = r.json()["id"]
    r = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": other_agent_id}, headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 403
    # NOTE: translated comment in English.
    r = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": pub_agent_id}, headers=headers)
    assert r.status_code == 200


def test_subscribe_requires_auth():
    """订阅任务需要登录"""
    # NOTE: translated comment in English.
    r = client.post(
        "/tasks/1/subscribe",
        json={"agent_id": 1},
    )
    assert r.status_code == 401


def test_agents_mine_requires_auth():
    """我的 Agent 需要登录"""
    r = client.get("/agents/mine")
    assert r.status_code == 401


def test_get_task_by_id():
    """获取单条任务详情（公开）"""
    # NOTE: translated comment in English.
    r = client.get("/tasks?limit=1")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    if not tasks:
        pytest.skip("no tasks in db")
    task_id = tasks[0]["id"]
    r = client.get(f"/tasks/{task_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == task_id
    assert "title" in data
    assert "publisher_name" in data


def test_account_balance_requires_auth():
    """账户余额需要登录"""
    r = client.get("/account/balance")
    assert r.status_code == 401


def test_account_me_and_balance():
    """登录后获取 /account/me 与余额"""
    u = f"baluser_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/account/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == u
    assert "user_id" in data
    assert "credits" in data
    tp = data.get("task_pulse") or {}
    assert tp.get("total_actionable") is not None
    assert "awaiting_verify_as_owner" in tp
    assert "need_submit" in tp
    assert "awaiting_confirm_as_assignee" in tp
    assert "disputes" in tp
    r = client.get("/account/balance", headers=headers)
    assert r.status_code == 200
    assert "credits" in r.json()


def test_recharge():
    """充值（模拟）"""
    u = f"recharge_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/account/recharge", json={"amount": 100}, headers=headers)
    assert r.status_code == 200
    assert r.json()["credits"] == 100


def test_recharge_order_credit_card():
    """充值订单：信用卡渠道创建订单并确认到账"""
    u = f"ordcard_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 50, "payment_method_type": "credit_card"},
        headers=headers,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["order_id"] and data["status"] == "pending"
    assert "payment_url" in data and data["payment_url"]
    r2 = client.post(
        "/account/recharge/confirm",
        json={"order_id": data["order_id"]},
        headers=headers,
    )
    assert r2.status_code == 200
    assert r2.json()["credits"] == 50


def test_recharge_order_alipay_bitcoin():
    """充值订单：支付宝返回 payment_qr，比特币返回 btc_address"""
    u = f"ordpay_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 20, "payment_method_type": "alipay"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json().get("payment_qr")
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 10, "payment_method_type": "bitcoin"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json().get("btc_address")


def test_publish_with_reward_requires_webhook():
    """有奖励点发布时必须填完成回调 URL"""
    u = f"webhook_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/tasks",
        json={"title": "有奖任务", "reward_points": 10},
        headers=headers,
    )
    assert r.status_code == 400
    assert "回调" in r.json().get("detail", "")


def test_publish_with_reward_and_webhook():
    """有奖励点 + 完成回调 URL 可发布成功"""
    u = f"pubreward_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/account/recharge", json={"amount": 50}, headers=headers)
    assert r.status_code == 200
    r = client.post(
        "/tasks",
        json={
            "title": "有奖任务",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/callback",
        },
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json().get("reward_points") == 10


def test_submit_completion_and_confirm():
    """接取者提交完成 -> 发布者验收通过（mock webhook）"""
    pub = f"pub_{_unique()}"
    exe = f"exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "验收测试任务",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]
    r = client.post(
        "/agents/register",
        json={"name": "执行Agent", "description": ""},
        headers=exe_headers,
    )
    assert r.status_code == 200
    agent_id = r.json()["id"]
    r = client.post(
        f"/tasks/{task_id}/subscribe",
        json={"agent_id": agent_id},
        headers=exe_headers,
    )
    assert r.status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        r = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "已完成"},
            headers=exe_headers,
        )
    assert r.status_code == 200
    assert "待验收" in r.json().get("message", "") or "提交" in r.json().get("message", "")
    r = client.post(f"/tasks/{task_id}/confirm", headers=pub_headers)
    assert r.status_code == 200
    r = client.get("/account/balance", headers=exe_headers)
    assert r.status_code == 200
    assert r.json()["credits"] == 5


def test_verification_methods_checklist_and_proof_link():
    """验收方式：hybrid 要求 proof_links + completed_requirements。"""
    pub = f"vpub_{_unique()}"
    exe = f"vexe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    r = client.post(
        "/tasks",
        json={
            "title": "混合验收任务",
            "description": "需要链接和清单",
            "verification_method": "hybrid",
            "verification_requirements": ["交付代码", "补充文档"],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    ag = client.post("/agents/register", json={"name": "verify-agent", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        bad = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "done", "evidence": {"proof_links": ["https://example.com/a"]}},
            headers=exe_headers,
        )
        assert bad.status_code == 400
        good = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={
                "result_summary": "done",
                "evidence": {
                    "proof_links": ["https://example.com/a"],
                    "completed_requirements": ["交付代码", "补充文档"],
                },
            },
            headers=exe_headers,
        )
    assert good.status_code == 200, good.text


def test_internal_messages_send_inbox_and_read():
    """站内信：用户可互发、查看收件箱并标记已读。"""
    a = f"msg_a_{_unique()}"
    b = f"msg_b_{_unique()}"
    _register_user(a, f"{a}@example.com", "pw")
    _register_user(b, f"{b}@example.com", "pw")
    a_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': a, 'password': 'pw'}).json()['access_token']}"}
    b_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': b, 'password': 'pw'}).json()['access_token']}"}

    s = client.post(
        "/messages",
        json={"recipient_username": b, "title": "你好", "content": "这是站内信"},
        headers=a_headers,
    )
    assert s.status_code == 200, s.text
    msg_id = s.json()["id"]

    inbox = client.get("/messages/inbox", headers=b_headers)
    assert inbox.status_code == 200
    items = inbox.json().get("items") or []
    assert any(int(x.get("id")) == int(msg_id) for x in items)
    assert (inbox.json().get("unread") or 0) >= 1

    mark = client.post(f"/messages/{msg_id}/read", headers=b_headers)
    assert mark.status_code == 200
    assert mark.json().get("is_read") is True

def test_reject_requires_reason():
    """拒绝验收时必须填写拒绝理由"""
    # NOTE: translated comment in English.
    u = f"rej_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/tasks/1/reject", json={}, headers=headers)
    # NOTE: translated comment in English.
    if r.status_code == 400:
        assert "理由" in r.json().get("detail", "")


def test_confirm_requires_publisher():
    """仅发布者可验收"""
    u = f"other_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    r = client.get("/tasks?limit=1")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    if not tasks:
        pytest.skip("no tasks")
    task_id = tasks[0]["id"]
    r = client.post(f"/tasks/{task_id}/confirm", headers=headers)
    assert r.status_code in (400, 403)


def test_agent_register_with_webhook_and_ping():
    """注册 Agent 时可填 webhook_url；探测存活：未配置或请求失败返回 alive=False"""
    u = f"pinguser_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/agents/register",
        json={"name": "PingAgent", "description": "test", "webhook_url": "https://example.com/webhook"},
        headers=headers,
    )
    assert r.status_code == 200
    agent_id = r.json()["id"]
    r = client.get(f"/agents/{agent_id}/ping", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "alive" in body
    # NOTE: translated comment in English.
    assert body["alive"] is False or body.get("reason") == "no_webhook"


def test_agent_send_message_requires_webhook():
    """未配置 Webhook 的 Agent 发消息应 400"""
    u = f"msguser_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/agents/register", json={"name": "NoWebhookAgent", "description": ""}, headers=headers)
    assert r.status_code == 200
    agent_id = r.json()["id"]
    r = client.post(f"/agents/{agent_id}/send-message", json={"content": "hello"}, headers=headers)
    assert r.status_code == 400
    assert "Webhook" in r.json().get("detail", "")


def test_publish_with_discord_webhook_optional():
    """发布任务时 discord_webhook_url 为可选，不报错即可（实际推送可 mock）"""
    u = f"discord_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 204
        r = client.post(
            "/tasks",
            json={
                "title": "Discord 推送测试",
                "description": "desc",
                "discord_webhook_url": "https://discord.com/api/webhooks/fake/fake",
            },
            headers=headers,
        )
    assert r.status_code == 200
    assert "id" in r.json()


def test_tasks_list_with_category_and_sort():
    """任务列表支持 category_filter、q、sort 参数"""
    r = client.get("/tasks", params={"category_filter": "development", "limit": 5})
    assert r.status_code == 200
    data = r.json()
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    r2 = client.get("/tasks", params={"q": "test", "sort": "reward_desc"})
    assert r2.status_code == 200
    assert "tasks" in r2.json()


def test_my_created_tasks_requires_auth():
    """我创建的任务需登录"""
    r = client.get("/tasks/created-by-me")
    assert r.status_code == 401


def test_my_created_tasks():
    """我创建的任务列表（登录后）"""
    u = f"created_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/tasks/created-by-me", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "tasks" in body
    assert "total" in body
    assert isinstance(body["tasks"], list)


def test_task_comments_list_and_post():
    """任务评论：列表公开，发表需登录"""
    u = f"comment_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # NOTE: translated comment in English.
    r = client.post("/tasks", json={"title": "评论测试任务", "description": "desc"}, headers=headers)
    assert r.status_code == 200
    task_id = r.json()["id"]
    # NOTE: translated comment in English.
    r = client.get(f"/tasks/{task_id}/comments")
    assert r.status_code == 200
    assert r.json()["comments"] == []
    # NOTE: translated comment in English.
    r = client.post(f"/tasks/{task_id}/comments", json={"content": "第一条评论"}, headers=headers)
    assert r.status_code == 200
    c = r.json()
    assert c["content"] == "第一条评论"
    assert c["author_name"] == u
    assert "id" in c
    # NOTE: translated comment in English.
    r = client.get(f"/tasks/{task_id}/comments")
    assert r.status_code == 200
    assert len(r.json()["comments"]) == 1
    assert r.json()["comments"][0]["content"] == "第一条评论"


def test_task_comment_post_requires_auth():
    """发表任务评论需登录"""
    r = client.get("/tasks")
    assert r.status_code == 200
    tasks = r.json().get("tasks") or []
    if not tasks:
        pytest.skip("no tasks in db")
    task_id = tasks[0]["id"]
    r = client.post(f"/tasks/{task_id}/comments", json={"content": "未登录评论"})
    assert r.status_code == 401


def test_escrow_two_milestones_partial_pay():
    """托管两里程碑：第一次验收部分放款且任务仍为进行中，第二次完成后结束。"""
    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "托管里程碑任务",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5},
                {"title": "阶段二", "weight": 0.5},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]
    r = client.post("/agents/register", json={"name": "托管执行Agent", "description": ""}, headers=exe_headers)
    assert r.status_code == 200
    agent_id = r.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段一交付"},
            headers=exe_headers,
        ).status_code == 200
    r = client.post(f"/tasks/{task_id}/confirm", headers=pub_headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("escrow", {}).get("finished") is False
    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "in_progress"
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段二交付"},
            headers=exe_headers,
        ).status_code == 200
    r = client.post(f"/tasks/{task_id}/confirm", headers=pub_headers)
    assert r.status_code == 200
    assert r.json().get("escrow", {}).get("finished") is True
    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "completed"


def test_escrow_dispute_blocks_submission():
    """托管争议：进入 disputed 后，接取者无法继续提交里程碑完成。"""
    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {
        "Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"
    }
    exe_headers = {
        "Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"
    }
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "托管争议冻结任务",
            "reward_points": 6,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5},
                {"title": "阶段二", "weight": 0.5},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]

    r = client.post("/agents/register", json={"name": "托管执行Agent", "description": ""}, headers=exe_headers)
    assert r.status_code == 200
    agent_id = r.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段一交付"},
            headers=exe_headers,
        ).status_code == 200

    reason = "阶段一提交证据不足，疑似不符合要求"
    evidence = {"summary": "提供了但疑似与验收不一致", "links": ["https://example.com/a", "https://example.com/b"]}
    r = client.post(
        f"/tasks/{task_id}/escrow/dispute",
        json={"reason": reason, "evidence": evidence},
        headers=pub_headers,
    )
    assert r.status_code == 200
    assert r.json().get("task_id") == task_id
    assert "冻结" in (r.json().get("message") or "")

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "disputed"
    assert td.get("escrow", {}).get("disputed") is True
    assert reason[:50] in (td.get("escrow", {}).get("dispute_reason") or "")
    assert (td.get("escrow", {}).get("dispute_evidence", {}) or {}).get("summary") is not None

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        r2 = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段二交付（不允许）"},
            headers=exe_headers,
        )
        assert r2.status_code == 400
        assert "争议中" in (r2.json().get("detail") or "")


def test_escrow_acceptance_criteria_saved():
    """里程碑 acceptance_criteria：发布后应在任务详情 escrow 摘要中回显。"""
    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {
        "Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"
    }

    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "托管里程碑验收要点任务",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5, "acceptance_criteria": "交付代码与测试"},
                {"title": "阶段二", "weight": 0.5, "acceptance_criteria": "补充文档与复盘"},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] in ("open", "in_progress")
    milestones = td.get("escrow", {}).get("milestones_preview") or []
    assert len(milestones) == 2
    assert milestones[0].get("acceptance_criteria") == "交付代码与测试"
    assert milestones[1].get("acceptance_criteria") == "补充文档与复盘"


def test_admin_force_confirm_escrow_dispute():
    """管理员 resolve: force_confirm 应直接按当前里程碑放款并推进任务状态。"""
    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    admin = f"esc_admin_{_unique()}"

    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    _register_user(admin, f"{admin}@example.com", "adminpw")

    pub_token = client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']
    exe_token = client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']
    admin_token = client.post('/auth/login', json={'username': admin, 'password': 'adminpw'}).json()['access_token']

    # NOTE: translated comment in English.
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == admin).first()
        assert u is not None
        u.is_superuser = True
        db.commit()
    finally:
        db.close()

    pub_headers = {"Authorization": f"Bearer {pub_token}"}
    exe_headers = {"Authorization": f"Bearer {exe_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "管理员强制验收争议任务",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5, "acceptance_criteria": "交付阶段一"},
                {"title": "阶段二", "weight": 0.5, "acceptance_criteria": "交付阶段二"},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]

    r = client.post("/agents/register", json={"name": "托管执行Agent", "description": ""}, headers=exe_headers)
    assert r.status_code == 200
    agent_id = r.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200

    # NOTE: translated comment in English.
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段一交付"},
            headers=exe_headers,
        ).status_code == 200

    # NOTE: translated comment in English.
    reason = "阶段一证据不足"
    r = client.post(
        f"/tasks/{task_id}/escrow/dispute",
        json={"reason": reason, "evidence": {"summary": "无充分证据"}},
        headers=pub_headers,
    )
    assert r.status_code == 200

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "disputed"

    # NOTE: translated comment in English.
    rr = client.post(
        f"/admin/tasks/{task_id}/escrow/dispute/resolve",
        json={"note": "管理员裁决：强制按当前里程碑验收", "resolution_type": "force_confirm"},
        headers=admin_headers,
    )
    assert rr.status_code == 200
    assert rr.json().get("resolution_type") == "force_confirm"

    td2 = client.get(f"/tasks/{task_id}").json()
    assert td2["status"] == "in_progress"
    assert td2.get("escrow", {}).get("disputed") is False


def test_publish_template_and_skill_version_tag():
    u = f"mk_pub_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post("/agents/register", json={"name": "模板Agent", "description": ""}, headers=headers)
    assert r.status_code == 200
    agent_id = r.json()["id"]

    # NOTE: translated comment in English.
    client.post("/account/recharge", json={"amount": 10}, headers=headers)
    create_task = client.post(
        "/tasks",
        json={"title": "用于模板发布", "reward_points": 1, "completion_webhook_url": "https://example.com/cb"},
        headers=headers,
    )
    task_id = create_task.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers).status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "ok"}, headers=headers).status_code == 200
    assert client.post(f"/tasks/{task_id}/confirm", headers=headers).status_code == 200

    pt = client.post(
        "/agent-templates",
        json={"agent_id": agent_id, "name": "模板A", "version_tag": "v1.2.0"},
        headers=headers,
    )
    assert pt.status_code == 200
    assert pt.json().get("version_tag") == "v1.2.0"

    # NOTE: translated comment in English.
    skill_token = f"sk_{_unique()}"
    r2 = client.post(
        "/agents/register",
        json={"name": "SkillAgent", "description": "", "skill_bound_token": skill_token},
        headers=headers,
    )
    assert r2.status_code == 200
    ps = client.post(
        "/skills/publish",
        json={"skill_token": skill_token, "name": "SkillA", "version_tag": "release-202603"},
        headers=headers,
    )
    assert ps.status_code == 200
    assert ps.json().get("version_tag") == "release-202603"


def test_admin_disputed_tasks_list():
    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    admin = f"esc_admin_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    _register_user(admin, f"{admin}@example.com", "adminpw")
    pub_token = client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']
    exe_token = client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']
    admin_token = client.post('/auth/login', json={'username': admin, 'password': 'adminpw'}).json()['access_token']

    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == admin).first()
        u.is_superuser = True
        db.commit()
    finally:
        db.close()

    pub_headers = {"Authorization": f"Bearer {pub_token}"}
    exe_headers = {"Authorization": f"Bearer {exe_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "争议列表测试任务",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [{"title": "阶段一", "weight": 0.5}, {"title": "阶段二", "weight": 0.5}],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200, r.json()
    task_id = r.json()["id"]
    ag = client.post("/agents/register", json={"name": "agent-x", "description": ""}, headers=exe_headers).json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag}, headers=exe_headers)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "done"}, headers=exe_headers)
    client.post(f"/tasks/{task_id}/escrow/dispute", json={"reason": "需要争议"}, headers=pub_headers)

    rr = client.get("/admin/tasks/disputed", headers=admin_headers)
    assert rr.status_code == 200
    items = rr.json().get("items") or []
    assert any(int(it.get("id", 0)) == task_id for it in items)


def test_account_api_keys_crud():
    u = f"ak_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    c = client.post(
        "/account/api-keys",
        json={"provider": "openai", "label": "主密钥", "secret": "sk-test-123456789"},
        headers=headers,
    )
    assert c.status_code == 200, c.text
    item_id = c.json().get("id")
    assert c.json().get("secret_masked")

    l = client.get("/account/api-keys", headers=headers)
    assert l.status_code == 200
    items = l.json().get("items") or []
    assert any(int(x.get("id", 0)) == int(item_id) for x in items)

    d = client.delete(f"/account/api-keys/{item_id}", headers=headers)
    assert d.status_code == 200
    assert d.json().get("ok") is True


def test_submit_completion_webhook_retry_success():
    """提交完成回调：首次网络错误后重试成功。"""
    pub = f"retry_pub_{_unique()}"
    exe = f"retry_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}

    client.post("/account/recharge", json={"amount": 10}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={"title": "webhook 重试任务", "reward_points": 5, "completion_webhook_url": "https://example.com/cb"},
        headers=pub_headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    ag = client.post("/agents/register", json={"name": "retry-agent", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx.Client") as client_cls:
        mock_client = client_cls.return_value.__enter__.return_value
        resp_ok = MagicMock()
        resp_ok.status_code = 200
        mock_client.post.side_effect = [httpx.RequestError("timeout"), resp_ok]
        s = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "done"},
            headers=exe_headers,
        )
        assert s.status_code == 200, s.text


def test_skill_tree_and_roi_series():
    u = f"tree_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    agent_id = client.post("/agents/register", json={"name": "tree-agent", "description": ""}, headers=headers).json()["id"]
    client.post("/account/recharge", json={"amount": 20}, headers=headers)
    t = client.post(
        "/tasks",
        json={
            "title": "tree task",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/cb",
            "skills": ["python", "fastapi"],
        },
        headers=headers,
    )
    task_id = t.json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "ok"}, headers=headers)
    client.post(f"/tasks/{task_id}/confirm", headers=headers)

    s1 = client.get(f"/agents/{agent_id}/skills", headers=headers)
    assert s1.status_code == 200
    assert len(s1.json().get("items") or []) >= 1

    s2 = client.get("/account/skill-tree", headers=headers)
    assert s2.status_code == 200
    assert len(s2.json().get("nodes") or []) >= 1

    rs = client.get("/stats/roi-series")
    assert rs.status_code == 200
    assert len(rs.json().get("series") or []) >= 7


def test_a2a_and_memory_endpoints_after_subscribe():
    """A2A 与 Memory：同一用户发布并接取后可访问 /a2a/*；Memory 写入与检索需登录"""
    u = f"a2mem_{_unique()}"
    email = f"{u}@example.com"
    data = _register_user(u, email, "pass123mem")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/tasks",
        json={"title": "A2A Memory E2E", "description": "api test"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    r = client.post(
        "/agents/register",
        json={"name": "A2A_Mem_Agent", "description": "e2e"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    agent_id = r.json()["id"]

    r = client.post(
        f"/tasks/{task_id}/subscribe",
        json={"agent_id": agent_id},
        headers=headers,
    )
    assert r.status_code == 200, r.text

    ra = client.get(f"/a2a/tasks/{task_id}", headers=headers)
    assert ra.status_code == 200, ra.text
    assert ra.json().get("id") == task_id

    rm = client.get(f"/a2a/tasks/{task_id}/messages", headers=headers)
    assert rm.status_code == 200, rm.text
    assert "messages" in rm.json()

    rp = client.post(
        f"/a2a/tasks/{task_id}/messages",
        json={"content": "e2e a2a ping", "kind": "message"},
        headers=headers,
    )
    assert rp.status_code == 200, rp.text

    mem = client.post(
        "/memory",
        json={"content": "e2e memory", "type": "text"},
        headers=headers,
    )
    assert mem.status_code == 200, mem.text

    ms = client.get("/memory/search", params={"query": "e2e"}, headers=headers)
    assert ms.status_code == 200, ms.text


def test_skill_contract_validate_and_publish_with_contract_profile():
    u = f"contract_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass1234")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    contract_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "enum": [10, 20]},
        },
        "required": ["query"],
    }
    failure = {"codes": [{"code": "RETRYABLE_TIMEOUT", "retryable": True}]}
    rv = client.post(
        "/skills/contract/validate",
        json={
            "contract_schema": contract_schema,
            "failure_semantics": failure,
            "sample_payload": {"query": "hello", "limit": 20},
        },
        headers=headers,
    )
    assert rv.status_code == 200, rv.text
    assert rv.json().get("ok") is True

    r_agent = client.post(
        "/agents/register",
        json={"name": "contract_agent", "skill_bound_token": "tok_contract_001"},
        headers=headers,
    )
    assert r_agent.status_code == 200, r_agent.text
    rp = client.post(
        "/skills/publish",
        json={
            "skill_token": "tok_contract_001",
            "name": "Contract Skill",
            "contract_schema": contract_schema,
            "failure_semantics": failure,
            "idempotency_hint": "hash(payload)",
        },
        headers=headers,
    )
    assert rp.status_code == 200, rp.text
    assert rp.json().get("contract_profile") is not None


def test_uploaded_skill_associated_with_task():
    u = f"skill_task_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass1234")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    skill_token = f"tok_{_unique()}"
    ar = client.post(
        "/agents/register",
        json={"name": "skill-linked-agent", "skill_bound_token": skill_token},
        headers=headers,
    )
    assert ar.status_code == 200, ar.text
    agent_id = int(ar.json()["id"])

    ps = client.post(
        "/skills/publish",
        json={"skill_token": skill_token, "name": "Linked Skill"},
        headers=headers,
    )
    assert ps.status_code == 200, ps.text
    skill_id = int(ps.json()["id"])

    tr = client.post(
        "/tasks",
        json={"title": "task with uploaded skill", "creator_agent_id": agent_id},
        headers=headers,
    )
    assert tr.status_code == 200, tr.text
    task_id = int(tr.json()["id"])

    td = client.get(f"/tasks/{task_id}", headers=headers)
    assert td.status_code == 200, td.text
    rel = td.json().get("related_skill") or {}
    assert rel.get("skill_token") == skill_token
    assert int(rel.get("skill_id")) == skill_id

    st = client.get(f"/skills/{skill_id}/tasks", headers=headers)
    assert st.status_code == 200, st.text
    ids = [int(x.get("id")) for x in (st.json().get("items") or [])]
    assert task_id in ids


def test_workflow_plan_attach_and_readiness():
    u = f"wf_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass1234")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    t1 = client.post("/tasks", json={"title": "wf-1", "description": "a"}, headers=headers)
    t2 = client.post("/tasks", json={"title": "wf-2", "description": "b"}, headers=headers)
    assert t1.status_code == 200 and t2.status_code == 200
    id1 = t1.json()["id"]
    id2 = t2.json()["id"]

    rp = client.post("/workflows/plan", json={"nodes": [id1, id2], "edges": [{"from": id1, "to": id2}]}, headers=headers)
    assert rp.status_code == 200, rp.text
    assert len(rp.json().get("topo_order") or []) == 2

    ra = client.post(f"/tasks/{id2}/workflow", json={"nodes": [id1, id2], "edges": [{"from": id1, "to": id2}]}, headers=headers)
    assert ra.status_code == 200, ra.text

    rg = client.get(f"/tasks/{id2}/workflow", headers=headers)
    assert rg.status_code == 200, rg.text
    assert rg.json().get("ready") is False
    assert id1 in (rg.json().get("blocked_by") or [])


def test_verification_chain_and_runtime_breakers_api():
    u = f"chain_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass1234")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    t = client.post("/tasks", json={"title": "chain task", "description": "x"}, headers=headers)
    assert t.status_code == 200, t.text
    task_id = t.json()["id"]

    rvc = client.get(f"/tasks/{task_id}/verification-chain", headers=headers)
    assert rvc.status_code == 200, rvc.text
    data = rvc.json()
    assert "declaration" in data and "sandbox" in data and "cross" in data

    rcb = client.get("/runtime/circuit-breakers", headers=headers)
    assert rcb.status_code == 200, rcb.text
    assert "items" in rcb.json()


def test_submit_confirm_reject_write_status_update_messages():
    u = f"statusmsg_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass1234")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    rt = client.post("/tasks", json={"title": "status-msg task", "description": "x"}, headers=headers)
    assert rt.status_code == 200, rt.text
    task_id = rt.json()["id"]
    ra = client.post("/agents/register", json={"name": "status_agent"}, headers=headers)
    assert ra.status_code == 200, ra.text
    agent_id = ra.json()["id"]
    rs = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers)
    assert rs.status_code == 200, rs.text

    rsub = client.post(
        f"/tasks/{task_id}/submit-completion",
        json={"result_summary": "done", "evidence": {"proof_links": []}},
        headers=headers,
    )
    assert rsub.status_code == 200, rsub.text
    rrej = client.post(f"/tasks/{task_id}/reject", json={"rejection_reason": "need update"}, headers=headers)
    assert rrej.status_code == 200, rrej.text
    rsub2 = client.post(
        f"/tasks/{task_id}/submit-completion",
        json={"result_summary": "done2", "evidence": {"proof_links": []}},
        headers=headers,
    )
    assert rsub2.status_code == 200, rsub2.text
    rcf = client.post(f"/tasks/{task_id}/confirm", json={"verification_mode": "manual_review"}, headers=headers)
    assert rcf.status_code == 200, rcf.text

    rc = client.get(f"/tasks/{task_id}/comments", headers=headers)
    assert rc.status_code == 200, rc.text
    kinds = [str(x.get("kind") or "") for x in (rc.json().get("comments") or [])]
    assert "status_update" in kinds


def test_runtime_circuit_breaker_control_for_admin():
    uid = _unique()
    admin = f"cb_admin_{uid}"
    _register_user(admin, f"{admin}@example.com", "adminpw")
    admin_token = client.post('/auth/login', json={'username': admin, 'password': 'adminpw'}).json()['access_token']

    from app.database.relational_db import SessionLocal
    from app.database.relational_db import User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == admin).first()
        assert u is not None
        u.is_superuser = True
        db.commit()
    finally:
        db.close()

    headers = {"Authorization": f"Bearer {admin_token}"}
    host = "example.com"
    ro = client.post("/runtime/circuit-breakers/control", json={"host": host, "action": "open"}, headers=headers)
    assert ro.status_code == 200, ro.text
    rc = client.post("/runtime/circuit-breakers/control", json={"host": host, "action": "close"}, headers=headers)
    assert rc.status_code == 200, rc.text
    rr = client.post("/runtime/circuit-breakers/control", json={"host": host, "action": "reset"}, headers=headers)
    assert rr.status_code == 200, rr.text


def test_forum_recent_posts_public_feed():
    u = f"forum_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "forum_pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/tasks", json={"title": "forum task", "description": "d"}, headers=headers)
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    pc = client.post(f"/tasks/{task_id}/comments", json={"content": "hello agent forum"}, headers=headers)
    assert pc.status_code == 200, pc.text
    fr = client.get("/forum/recent-posts", params={"limit": 20})
    assert fr.status_code == 200, fr.text
    data = fr.json()
    assert "items" in data and "total" in data
    assert any(
        (it.get("comment") or {}).get("content") == "hello agent forum"
        for it in (data.get("items") or [])
    )
    assert any(int((it.get("task") or {}).get("id", 0)) == task_id for it in (data.get("items") or []))


def test_verification_hours_extend_and_task_detail_extras():
    """任务级验收窗口、延长验收、详情含 timeline / payment_breakdown"""
    u = f"vh_{_unique()}"
    pub = _register_user(u, f"{u}@example.com", "vh_pw")
    token = pub["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/account/recharge", json={"amount": 5000}, headers=headers)
    assert r.status_code == 200, r.text
    pr = client.post(
        "/tasks",
        json={
            "title": "vh task",
            "description": "d",
            "reward_points": 100,
            "completion_webhook_url": "https://example.com/hook",
            "verification_hours": 24,
        },
        headers=headers,
    )
    assert pr.status_code == 200, pr.text
    task_id = pr.json()["id"]
    gd = client.get(f"/tasks/{task_id}")
    assert gd.status_code == 200
    assert gd.json().get("verification_hours") == 24
    assert isinstance(gd.json().get("timeline"), list)
    assert gd.json().get("payment_breakdown", {}).get("reward_points") == 100

    exe = _register_user(f"exe_{_unique()}", f"exe_{_unique()}@example.com", "pw")
    ex_headers = {"Authorization": f"Bearer {exe['access_token']}"}
    ar = client.post("/agents/register", json={"name": "ag", "agent_type": "general"}, headers=ex_headers)
    assert ar.status_code == 200, ar.text
    aid = ar.json()["id"]
    sub = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": aid}, headers=ex_headers)
    assert sub.status_code == 200, sub.text
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        sc = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "done"},
            headers=ex_headers,
        )
    assert sc.status_code == 200, sc.text
    assert sc.json().get("verification_hours") == 24
    ext = client.post(f"/tasks/{task_id}/extend-verification", headers=headers)
    assert ext.status_code == 200, ext.text
    ext2 = client.post(f"/tasks/{task_id}/extend-verification", headers=headers)
    assert ext2.status_code == 400

    bc = client.post("/tasks/batch-confirm", json={"task_ids": [task_id]}, headers=headers)
    assert bc.status_code == 200, bc.text
    assert "summary" in bc.json()
