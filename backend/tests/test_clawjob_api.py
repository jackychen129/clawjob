"""
ClawJob API 功能测试：认证、任务大厅、发布任务、注册 Agent、订阅任务、账户、验收流程。
"""
import os
import time
from typing import Optional
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
import httpx
from fastapi.testclient import TestClient

# 测试环境关闭后台 community 循环，避免 stats 计数在 before/after 之间被异步任务扰动
os.environ.setdefault("CLAWJOB_COMMUNITY_BACKGROUND_JOBS", "0")
# 默认使用 sqlite，避免本地/CI 未启动 Postgres 时卡住
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_clawjob_api.db")

from app.main import app
import app.main as app_main
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


def test_showcase_completion_webhook_accepts_post():
    """展示任务完成回调端点接受 POST（避免 /health 405）"""
    r = client.post(
        "/webhooks/showcase-completion",
        json={"task_id": 1, "result_summary": "test"},
    )
    assert r.status_code == 200
    assert r.json().get("ok") is True


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
    assert "agents_count_public" in data
    assert "agents_count_total" in data
    assert data["agents_count"] == data["agents_count_public"]
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


def test_register_agent_minimal_success():
    """最低摩擦注册：无 second_task，握手自动完成，500 赠点。"""
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": "MinimalAgent", "description": "pytest minimal"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("username", "").startswith("skill_")
    assert data.get("signup_bonus_credits") == 500
    assert data.get("credits") == 500
    assert data.get("agent_id")
    tasks = data.get("auto_published_tasks") or []
    assert len(tasks) == 1
    assert tasks[0].get("status") == "completed"
    assert data.get("next_steps", {}).get("tasks_hall_url")
    token = data["access_token"]
    me = client.get("/account/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json().get("credits") == 500


def test_register_agent_minimal_duplicate_name_gets_suffix():
    """同名 agent_name 可重复注册；第二条会带后缀。"""
    name = f"DupName_{_unique()}"
    r1 = client.post("/auth/register-agent-minimal", json={"agent_name": name})
    assert r1.status_code == 200, r1.text
    assert r1.json().get("agent_name") == name
    r2 = client.post("/auth/register-agent-minimal", json={"agent_name": name})
    assert r2.status_code == 200, r2.text
    name2 = r2.json().get("agent_name") or ""
    assert name2.startswith(name)
    assert name2 != name or "-" in name2


def test_register_agent_minimal_referral(monkeypatch):
    """register-agent-minimal 支持 referral_code。"""
    monkeypatch.setenv("REFERRAL_BONUS_REFERRER", "100")
    monkeypatch.setenv("REFERRAL_BONUS_INVITEE", "50")
    ref = f"refmin_{_unique()}"
    tk_ref = _register_user(ref, f"{ref}@example.com", "pw")["access_token"]
    my = client.get("/account/referral", headers={"Authorization": f"Bearer {tk_ref}"}).json()
    code = my.get("referral_code") or my.get("code")
    if not code:
        pytest.skip("referral_code not available in test env")
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"RefMin_{_unique()}", "referral_code": code},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("referral_bound") is True


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
    # 定向任务：发布时带 invited_agent_ids 应自动 invitees_only
    r = client.get(f"/tasks/{task_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body.get("visibility") == "invitees_only"


def test_creator_studio_requires_auth():
    r = client.get("/agents/mine/studio")
    assert r.status_code == 401


def test_creator_studio_returns_summary():
    u = f"studio_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    r = client.post("/agents/register", json={"name": "StudioAgent", "description": "x"}, headers=headers)
    assert r.status_code == 200
    rs = client.get("/agents/mine/studio?days=14", headers=headers)
    assert rs.status_code == 200
    body = rs.json()
    assert body["summary"]["agents_count"] == 1
    assert isinstance(body["income_series"], list)
    assert len(body["income_series"]) == 14


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


def test_task_confirm_sends_community_closure_inbox_and_flag():
    """验收结案：站内信引导进社区 + output_data 幂等标记。"""
    pub = f"pub_cc_{_unique()}"
    exe = f"exe_cc_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "闭环站内信任务",
            "reward_points": 3,
            "completion_webhook_url": "https://example.com/cb",
            "category": "development",
        },
        headers=pub_headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    agent_id = client.post("/agents/register", json={"name": "执行A", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "ok"},
            headers=exe_headers,
        ).status_code == 200
    assert client.post(f"/tasks/{task_id}/confirm", headers=pub_headers).status_code == 200

    pub_inbox = client.get("/messages/inbox", headers=pub_headers)
    assert pub_inbox.status_code == 200
    pub_titles = [str(x.get("title") or "") for x in (pub_inbox.json().get("items") or [])]
    assert any("社区" in t or "复盘" in t for t in pub_titles), pub_titles

    exe_inbox = client.get("/messages/inbox", headers=exe_headers)
    assert exe_inbox.status_code == 200
    exe_titles = [str(x.get("title") or "") for x in (exe_inbox.json().get("items") or [])]
    assert any("验收" in t or "任务" in t for t in exe_titles), exe_titles

    td = client.get(f"/tasks/{task_id}").json()
    assert (td.get("output_data") or {}).get("community_hooks_completed_v1") is True


def test_skill_task_completion_post_publisher():
    """POST /community/skill/task-completion-post：发布方对已结案任务发帖。"""
    pub = f"pub_sk_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    r = client.post(
        "/tasks",
        json={"title": "Skill闭环发帖", "reward_points": 0, "category": "other"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    assert client.post(f"/tasks/{task_id}/confirm", headers=headers).status_code == 200

    ag = client.post("/agents/register", json={"name": "PubAgent", "description": ""}, headers=headers).json()
    pr = client.post(
        "/community/skill/task-completion-post",
        json={"task_id": task_id, "agent_id": ag["id"], "content": "复盘：本条由测试发帖。", "intent": "recap"},
        headers=headers,
    )
    assert pr.status_code == 200, pr.text
    assert pr.json().get("type") == "community_message"
    tid = pr.json().get("topic_id")
    assert tid
    msgs = client.get(f"/community/topics/{tid}/messages").json().get("items") or []
    assert any("复盘：本条由测试发帖。" in str(x.get("content_md") or "") for x in msgs)


def test_execute_task_retry_observability_saved():
    """执行重试后应在任务 output_data.last_execute 留存 retried/ok。"""
    u = f"exec_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/tasks",
        json={"title": "执行重试观测任务", "description": "x", "reward_points": 0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    mocked = AsyncMock(side_effect=[RuntimeError("boom"), {"ok": True}])
    with patch("app.main.task_system.execute_task", new=mocked):
        ex = client.post(f"/tasks/{task_id}/execute?retry_count=1", headers=headers)
        assert ex.status_code == 200, ex.text
        assert ex.json().get("retried") == 1

    td = client.get(f"/tasks/{task_id}").json()
    le = ((td.get("output_data") or {}).get("last_execute") or {})
    assert le.get("ok") is True
    assert int(le.get("retried") or 0) == 1
    assert isinstance(le.get("at"), str) and le.get("at")


def test_execute_task_retry_observability_failed_saved():
    """执行最终失败时也应记录 output_data.last_execute（ok=false + error）。"""
    u = f"exec_fail_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/tasks",
        json={"title": "执行失败观测任务", "description": "x", "reward_points": 0},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    mocked = AsyncMock(side_effect=RuntimeError("still boom"))
    with patch("app.main.task_system.execute_task", new=mocked):
        ex = client.post(f"/tasks/{task_id}/execute?retry_count=2", headers=headers)
        assert ex.status_code == 500, ex.text
        assert "已重试 2 次" in (ex.json().get("detail") or "")

    td = client.get(f"/tasks/{task_id}").json()
    le = ((td.get("output_data") or {}).get("last_execute") or {})
    assert le.get("ok") is False
    assert int(le.get("retried") or -1) == 2
    assert "still boom" in (le.get("error") or "")
    assert isinstance(le.get("at"), str) and le.get("at")


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
    precheck = (td.get("escrow", {}) or {}).get("dispute_ai_precheck") or {}
    assert precheck.get("summary")
    assert precheck.get("recommendation")

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
    tl = td2.get("timeline") or []
    assert any((e.get("type") == "admin_escrow_resolved") for e in tl), tl


def test_admin_resume_escrow_dispute_timeline():
    """管理员 resolve: resume 解除冻结后 timeline 含 admin_escrow_resumed。"""
    from app.database.relational_db import SessionLocal, User as UserModel

    pub = f"esc_pub_{_unique()}"
    exe = f"esc_exe_{_unique()}"
    admin = f"esc_admin_{_unique()}"

    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    _register_user(admin, f"{admin}@example.com", "adminpw")

    admin_token = client.post("/auth/login", json={"username": admin, "password": "adminpw"}).json()["access_token"]
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == admin).first()
        assert u is not None
        u.is_superuser = True
        db.commit()
    finally:
        db.close()

    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "管理员恢复争议任务",
            "reward_points": 8,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5},
                {"title": "阶段二", "weight": 0.5},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    agent_id = client.post("/agents/register", json={"name": "恢复测试Agent", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段一交付"},
            headers=exe_headers,
        ).status_code == 200

    assert client.post(
        f"/tasks/{task_id}/escrow/dispute",
        json={"reason": "需管理员介入", "evidence": {"summary": "证据"}},
        headers=pub_headers,
    ).status_code == 200

    rr = client.post(
        f"/admin/tasks/{task_id}/escrow/dispute/resolve",
        json={"note": "恢复执行", "resolution_type": "resume"},
        headers=admin_headers,
    )
    assert rr.status_code == 200

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "in_progress"
    tl = td.get("timeline") or []
    assert any((e.get("type") == "admin_escrow_resumed") for e in tl), tl


def test_timeline_auto_confirm_non_escrow():
    """待验收超时：GET 任务详情触发自动验收，timeline 含 auto_confirmed。"""
    from datetime import datetime, timedelta
    from app.database.relational_db import SessionLocal, Task as TaskModel

    pub = f"auto_{_unique()}"
    exe = f"autoexe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "自动验收时间线任务",
            "reward_points": 4,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=pub_headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]
    agent_id = client.post("/agents/register", json={"name": "AutoExe", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "已完成"},
            headers=exe_headers,
        ).status_code == 200

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t is not None
        t.verification_deadline_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "completed"
    tl = td.get("timeline") or []
    assert any((e.get("type") == "auto_confirmed") for e in tl), tl


def test_timeline_auto_milestone_escrow():
    """托管多里程碑：首阶段待验收超时后 GET 详情触发自动确认，timeline 含 auto_milestone_confirmed，任务进入下一阶段 in_progress。"""
    from datetime import datetime, timedelta
    from app.database.relational_db import SessionLocal, Task as TaskModel

    pub = f"auto_esc_{_unique()}"
    exe = f"auto_escexe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=pub_headers)
    r = client.post(
        "/tasks",
        json={
            "title": "托管自动里程碑时间线",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "阶段一", "weight": 0.5},
                {"title": "阶段二", "weight": 0.5},
            ],
        },
        headers=pub_headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    agent_id = client.post("/agents/register", json={"name": "EscAutoExe", "description": ""}, headers=exe_headers).json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200

    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "阶段一交付"},
            headers=exe_headers,
        ).status_code == 200

    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t is not None
        t.verification_deadline_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "in_progress"
    tl = td.get("timeline") or []
    hit = [e for e in tl if e.get("type") == "auto_milestone_confirmed"]
    assert hit, tl
    assert "全部里程碑已完成" not in (hit[-1].get("summary") or "")


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


def test_agent_skills_readable_without_login():
    """GET /agents/{id}/skills 无需登录即可浏览（公开主页）；折旧策略详情仅拥有者响应中包含 policy。"""
    u = f"skill_pub_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post("/auth/login", json={"username": u, "password": "pw"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    agent_id = client.post("/agents/register", json={"name": "pub-skill-agent", "description": ""}, headers=headers).json()["id"]
    client.post("/account/recharge", json={"amount": 20}, headers=headers)
    t = client.post(
        "/tasks",
        json={
            "title": "public skill task",
            "reward_points": 6,
            "completion_webhook_url": "https://example.com/cb",
            "skills": ["python"],
        },
        headers=headers,
    )
    task_id = t.json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "ok"}, headers=headers)
    client.post(f"/tasks/{task_id}/confirm", headers=headers)

    r_anon = client.get(f"/agents/{agent_id}/skills")
    assert r_anon.status_code == 200, r_anon.text
    body_anon = r_anon.json()
    assert body_anon.get("viewer_is_owner") is False
    assert "policy" not in (body_anon.get("decay") or {})

    r_owner = client.get(f"/agents/{agent_id}/skills", headers=headers)
    assert r_owner.status_code == 200
    body_own = r_owner.json()
    assert body_own.get("viewer_is_owner") is True
    pol = (body_own.get("decay") or {}).get("policy") or {}
    assert int(pol.get("idle_days") or 0) >= 1


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


def test_skill_tree_decay_meta_present():
    """技能树响应应包含 decay 元信息；历史任务应产生折旧比率。"""
    from datetime import datetime, timedelta
    from app.database.relational_db import SessionLocal, Task as TaskModel

    u = f"tree_decay_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw")
    token = client.post('/auth/login', json={'username': u, 'password': 'pw'}).json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}

    agent_id = client.post("/agents/register", json={"name": "tree-decay-agent", "description": ""}, headers=headers).json()["id"]
    client.post("/account/recharge", json={"amount": 20}, headers=headers)
    t = client.post(
        "/tasks",
        json={
            "title": "tree decay task",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "skills": ["python"],
        },
        headers=headers,
    )
    task_id = t.json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "ok"}, headers=headers)
    client.post(f"/tasks/{task_id}/confirm", headers=headers)

    db = SessionLocal()
    try:
        row = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert row is not None
        row.completed_at = datetime.utcnow() - timedelta(days=60)
        db.commit()
    finally:
        db.close()

    s1 = client.get(f"/agents/{agent_id}/skills", headers=headers)
    assert s1.status_code == 200
    decay1 = s1.json().get("decay") or {}
    assert float(decay1.get("ratio") or 0) > 0
    assert decay1.get("last_active_at")
    policy1 = decay1.get("policy") or {}
    assert int(policy1.get("idle_days") or 0) >= 1
    assert float(policy1.get("weekly_ratio") or 0) >= 0
    assert float(policy1.get("max_ratio") or 0) >= float(policy1.get("weekly_ratio") or 0)

    s2 = client.get("/account/skill-tree", headers=headers)
    assert s2.status_code == 200
    decay2 = s2.json().get("decay") or {}
    assert float(decay2.get("max_ratio") or 0) > 0
    assert decay2.get("last_active_at")
    policy2 = decay2.get("policy") or {}
    assert int(policy2.get("idle_days") or 0) >= 1
    assert float(policy2.get("weekly_ratio") or 0) >= 0
    assert float(policy2.get("max_ratio") or 0) >= float(policy2.get("weekly_ratio") or 0)


def test_skill_decay_env_parser_fallback():
    """折旧配置读取应容错：非法环境变量不应导致异常，且回落默认值。"""
    from app.main import _env_float, _env_int
    with patch.dict(os.environ, {"SKILL_DECAY_IDLE_DAYS": "bad", "SKILL_DECAY_WEEKLY_RATIO": "x", "SKILL_DECAY_MAX_RATIO": ""}, clear=False):
        assert _env_int("SKILL_DECAY_IDLE_DAYS", 14, min_value=1) == 14
        assert _env_float("SKILL_DECAY_WEEKLY_RATIO", 0.02, min_value=0.0, max_value=1.0) == 0.02
        assert _env_float("SKILL_DECAY_MAX_RATIO", 0.2, min_value=0.0, max_value=1.0) == 0.2


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

    # Escrow milestones in verification chain (acceptance_criteria)
    pub2 = f"chain_esc_{_unique()}"
    _register_user(pub2, f"{pub2}@example.com", "pass1234")
    h2 = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub2, 'password': 'pass1234'}).json()['access_token']}"}
    client.post("/account/recharge", json={"amount": 20}, headers=h2)
    te = client.post(
        "/tasks",
        json={
            "title": "chain escrow",
            "description": "x",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "M1", "weight": 0.5, "acceptance_criteria": "Deliver API spec"},
                {"title": "M2", "weight": 0.5, "acceptance_criteria": "Ship code"},
            ],
        },
        headers=h2,
    )
    assert te.status_code == 200, te.text
    eid = te.json()["id"]
    rvc2 = client.get(f"/tasks/{eid}/verification-chain", headers=h2)
    assert rvc2.status_code == 200
    decl = rvc2.json().get("declaration") or {}
    ms = decl.get("escrow_milestones") or []
    assert len(ms) == 2
    assert ms[0].get("acceptance_criteria") == "Deliver API spec"

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


def test_publish_fee_estimate_and_breakdown_consistency():
    """发布前费用估算接口：字段齐全，与发布路径的扣款口径一致"""
    u = f"fee_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 100}, headers=headers)
    r = client.get("/account/publish-fee-estimate", params={"reward_points": 40}, headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    for k in (
        "reward_points",
        "commission_rate",
        "commission_points",
        "executor_net_points",
        "publisher_credits",
        "publisher_credits_after",
        "sufficient",
        "max_reward_points",
    ):
        assert k in data, f"缺少字段 {k}"
    assert data["reward_points"] == 40
    assert data["publisher_credits"] == 100
    assert data["publisher_credits_after"] == 60
    assert data["sufficient"] is True
    assert data["commission_points"] + data["executor_net_points"] == data["reward_points"]

    r2 = client.get("/account/publish-fee-estimate", params={"reward_points": 500}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["sufficient"] is False


def test_publish_task_insufficient_credits_no_deduction_or_ghost_task():
    """余额不足时：不应创建任务、不应产生扣款流水"""
    u = f"nopay_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 5}, headers=headers)
    before_balance = client.get("/account/balance", headers=headers).json()["credits"]
    r = client.post(
        "/tasks",
        json={
            "title": "超额任务",
            "reward_points": 100,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    assert r.status_code == 400
    after_balance = client.get("/account/balance", headers=headers).json()["credits"]
    assert after_balance == before_balance, "余额不足时不应扣款"
    txs = client.get("/account/transactions", headers=headers).json().get("transactions", [])
    assert not any(t.get("type") == "task_publish" for t in txs), "余额不足时不应有 task_publish 流水"


def test_publish_task_atomic_deduction_and_single_tx():
    """发布成功：扣款精确等于 reward_points，且恰好产生一条 task_publish 流水"""
    u = f"atomic_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 80}, headers=headers)
    before = client.get("/account/balance", headers=headers).json()["credits"]
    r = client.post(
        "/tasks",
        json={
            "title": "原子扣款任务",
            "reward_points": 30,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    after = client.get("/account/balance", headers=headers).json()["credits"]
    assert before - after == 30, f"扣款应等于奖励点：before={before}, after={after}"
    txs = client.get("/account/transactions", headers=headers).json().get("transactions", [])
    publish_txs = [t for t in txs if t.get("type") == "task_publish" and t.get("ref_id") == task_id]
    assert len(publish_txs) == 1, f"应恰好产生一条 task_publish 流水，实际 {len(publish_txs)}"
    assert publish_txs[0]["amount"] == -30


def test_publish_task_reward_cap():
    """奖励点超过单任务上限 -> 400"""
    u = f"cap_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    from app.main import MAX_TASK_REWARD_POINTS

    r = client.post(
        "/tasks",
        json={
            "title": "超大奖励任务",
            "reward_points": MAX_TASK_REWARD_POINTS + 1,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    assert r.status_code == 400


def test_recharge_methods_catalog_lists_multiple_channels():
    """渠道目录返回多种支付方式，含关键字段与新增渠道"""
    r = client.get("/account/recharge/methods")
    assert r.status_code == 200
    methods = r.json().get("methods") or []
    keys = {m["key"] for m in methods}
    assert "alipay" in keys
    assert "wechat_pay" in keys
    assert "paypal" in keys
    assert "usdt_trc20" in keys
    assert "bank_transfer" in keys
    sample = methods[0]
    for k in ("key", "display_name", "kind", "min_amount", "max_amount", "fee_rate"):
        assert k in sample


def test_recharge_order_wechat_pay():
    """微信支付渠道返回 payment_qr + instructions.qr_payload"""
    u = f"wx_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 30, "payment_method_type": "wechat_pay"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["payment_qr"]
    inst = data.get("instructions") or {}
    assert inst.get("kind") == "qr"
    assert "qr_payload" in inst


def test_recharge_order_paypal_returns_url():
    u = f"pp_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 50, "payment_method_type": "paypal"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["payment_url"] and "paypal" in data["payment_url"]
    assert data["instructions"]["kind"] == "url"


def test_recharge_order_bank_transfer_returns_bank_details():
    u = f"bank_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 500, "payment_method_type": "bank_transfer"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    inst = r.json()["instructions"]
    assert inst["kind"] == "bank"
    bank = inst.get("bank") or {}
    for k in ("bank_name", "account_name", "account_number", "memo"):
        assert k in bank


def test_recharge_order_usdt_returns_crypto_address():
    u = f"usdt_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 200, "payment_method_type": "usdt_trc20"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["btc_address"] and data["btc_address"].startswith("T")
    inst = data["instructions"]
    assert inst["kind"] == "crypto"
    assert inst["crypto"]["network"].startswith("TRON")


def test_recharge_order_bank_min_amount_enforced():
    u = f"bmin_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 10, "payment_method_type": "bank_transfer"},
        headers=headers,
    )
    assert r.status_code == 400
    assert "最低" in r.json().get("detail", "")


def test_recharge_order_unknown_method_rejected():
    u = f"unk_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 20, "payment_method_type": "unknown_channel"},
        headers=headers,
    )
    assert r.status_code == 400


def test_bind_payment_method_supports_new_channels():
    u = f"bind_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for kind, masked in (
        ("wechat_pay", "wx-openid-****abcd"),
        ("paypal", "user***@example.com"),
        ("usdt_trc20", "T****xyz"),
    ):
        r = client.post(
            "/account/payment-methods",
            json={"type": kind, "masked_info": masked},
            headers=headers,
        )
        assert r.status_code == 200, f"{kind}: {r.text}"
        assert r.json()["type"] == kind


def test_recharge_confirm_is_idempotent():
    """重复调用 /recharge/confirm 不应造成双倍到账"""
    u = f"idem_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post(
        "/account/recharge/orders",
        json={"amount": 77, "payment_method_type": "credit_card"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    order_id = r.json()["order_id"]
    r1 = client.post("/account/recharge/confirm", json={"order_id": order_id}, headers=headers)
    assert r1.status_code == 200
    balance1 = r1.json()["credits"]
    r2 = client.post("/account/recharge/confirm", json={"order_id": order_id}, headers=headers)
    assert r2.status_code == 200, r2.text
    balance2 = r2.json()["credits"]
    assert balance2 == balance1, "重复确认不应再次加款"
    assert r2.json().get("idempotent") is True
    txs = client.get("/account/transactions", headers=headers).json().get("transactions", [])
    order_txs = [t for t in txs if t.get("type") == "recharge" and t.get("ref_id") == order_id]
    assert len(order_txs) == 1, "重复确认不应产生第二条充值流水"


# ---------------------------------------------------------------------------
# Phase A-1：发布方撤单退款
# ---------------------------------------------------------------------------


def test_cancel_task_refunds_points_atomically():
    """未接取任务撤单：余额原子回退，状态置为 cancelled_refunded，并写 task_publish_refund 流水。"""
    u = f"cancel_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 100}, headers=headers)
    before = client.get("/account/balance", headers=headers).json()["credits"]
    r = client.post(
        "/tasks",
        json={
            "title": "待撤单任务",
            "reward_points": 40,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]
    mid = client.get("/account/balance", headers=headers).json()["credits"]
    assert before - mid == 40

    rc = client.post(f"/tasks/{task_id}/cancel", headers=headers)
    assert rc.status_code == 200, rc.text
    data = rc.json()
    assert data["ok"] is True
    assert data["status"] == "cancelled_refunded"
    assert data["refunded_points"] == 40
    assert data["idempotent"] is False

    after = client.get("/account/balance", headers=headers).json()["credits"]
    assert after == before, f"撤单后应完全退回：before={before}, after={after}"

    txs = client.get("/account/transactions", headers=headers).json().get("transactions", [])
    refund_txs = [t for t in txs if t.get("type") == "task_publish_refund" and t.get("ref_id") == task_id]
    assert len(refund_txs) == 1
    assert refund_txs[0]["amount"] == 40


def test_cancel_task_is_idempotent():
    """重复撤单不应二次退款。"""
    u = f"cancel_idem_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 60}, headers=headers)
    r = client.post(
        "/tasks",
        json={
            "title": "幂等撤单任务",
            "reward_points": 20,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    task_id = r.json()["id"]
    rc1 = client.post(f"/tasks/{task_id}/cancel", headers=headers)
    assert rc1.status_code == 200 and rc1.json()["refunded_points"] == 20
    b1 = client.get("/account/balance", headers=headers).json()["credits"]
    rc2 = client.post(f"/tasks/{task_id}/cancel", headers=headers)
    assert rc2.status_code == 200
    assert rc2.json()["idempotent"] is True
    assert rc2.json()["refunded_points"] == 0
    b2 = client.get("/account/balance", headers=headers).json()["credits"]
    assert b1 == b2, "重复撤单不应再次加款"
    txs = client.get("/account/transactions", headers=headers).json().get("transactions", [])
    refund_txs = [t for t in txs if t.get("type") == "task_publish_refund" and t.get("ref_id") == task_id]
    assert len(refund_txs) == 1


def test_cancel_task_rejected_when_already_accepted():
    """已被接取的任务不可撤单。"""
    u = f"cancel_block_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    client.post("/account/recharge", json={"amount": 50}, headers=headers)
    r = client.post(
        "/tasks",
        json={
            "title": "被接取任务",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=headers,
    )
    task_id = r.json()["id"]
    # NOTE: 发布方自建 Agent 并接取任务
    ar = client.post("/agents/register", json={"name": "mine", "description": "d"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    sr = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=headers)
    assert sr.status_code == 200, sr.text
    rc = client.post(f"/tasks/{task_id}/cancel", headers=headers)
    assert rc.status_code == 400
    assert "接取" in rc.json()["detail"]


def test_agent_reputation_public_readable_and_empty_is_baseline():
    """匿名可读；无接单记录的新 Agent 评分为基础 60。"""
    u = f"rep_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post("/agents/register", json={"name": "rep-agent", "description": "d"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]

    # NOTE: 匿名访问（不带 token）
    r = client.get(f"/agents/{agent_id}/reputation")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent"]["id"] == agent_id
    assert data["agent"]["owner"]["username"]
    assert data["reputation_score"] == 60
    stats = data["stats"]
    assert stats["accepted_task_count"] == 0
    assert stats["completed_task_count"] == 0
    assert stats["first_pass_confirm_rate"] is None


def test_agent_reputation_reflects_completed_tasks():
    """完成任务后信誉卡的 completed / reward_points_total / first_pass_confirm_rate 同步更新。"""
    pub = f"reppub_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 50}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={
            "title": "rep-task",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h_pub,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]

    exe = f"repexec_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    ar = client.post("/agents/register", json={"name": "doer", "description": "d"}, headers=h_exe)
    agent_id = ar.json()["id"]
    sr = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=h_exe)
    assert sr.status_code == 200, sr.text
    # NOTE: 直接把任务状态置为 completed，避免串上 submit-completion 的 webhook 依赖
    from app.database.relational_db import SessionLocal, Task
    from datetime import datetime
    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == task_id).first()
        t.status = "completed"
        t.completed_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()

    r = client.get(f"/agents/{agent_id}/reputation")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["stats"]["accepted_task_count"] >= 1
    assert data["stats"]["completed_task_count"] >= 1
    assert data["stats"]["reward_points_total"] >= 10
    assert data["stats"]["first_pass_confirm_rate"] == 1.0
    assert data["reputation_score"] >= 80, f"完成+首过 expected ≥80, got {data['reputation_score']}"


def test_agent_reputation_404_for_missing():
    r = client.get("/agents/99999999/reputation")
    assert r.status_code == 404


def test_agent_trust_card_public():
    """信任卡匿名可读，含完成率、徽章与 URL。"""
    u = f"trust_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post("/agents/register", json={"name": "trust-agent", "description": "d"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    r = client.get(f"/agents/{agent_id}/trust-card")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent_id"] == agent_id
    assert "completion_rate" in data
    assert "escrow_tasks_completed" in data
    assert "verified_skills" in data
    assert "badges" in data
    assert data["urls"]["trust_card"]


def test_task_list_includes_escrow_and_payout_badges():
    pub = f"badgepub_{_unique()}"
    tk = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h)
    tr = client.post(
        "/tasks",
        json={
            "title": "escrow-badge-task",
            "reward_points": 20,
            "completion_webhook_url": "https://example.com/cb",
            "escrow_milestones": [
                {"title": "M1", "weight": 0.5, "acceptance_criteria": "done"},
                {"title": "M2", "weight": 0.5, "acceptance_criteria": "done"},
            ],
        },
        headers=h,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]
    detail = client.get(f"/tasks/{task_id}")
    assert detail.status_code == 200, detail.text
    d = detail.json()
    assert d.get("escrow", {}).get("enabled") is True
    badges = d.get("badges") or []
    assert "escrow" in badges
    assert "verified_payout" in badges
    lst = client.get("/tasks", params={"status_filter": "open"})
    assert lst.status_code == 200
    row = next((t for t in lst.json().get("tasks", []) if t["id"] == task_id), None)
    assert row is not None
    assert "verified_payout" in (row.get("badges") or [])


def test_skill_pack_recommended_tasks():
    r = client.get("/skills/packs/openclaw-starter/recommended-tasks", params={"limit": 5})
    assert r.status_code == 200, r.text
    assert r.json().get("pack_id") == "openclaw-starter"
    assert "tasks" in r.json()
    r404 = client.get("/skills/packs/no-such-pack/recommended-tasks")
    assert r404.status_code == 404


def test_recommend_candidates_top_k_owner_only():
    """发布方可获取 Top-K 候选人推荐；非发布者 403。"""
    pub = f"reccpub_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 50}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={
            "title": "rec-task",
            "reward_points": 15,
            "completion_webhook_url": "https://example.com/cb",
            "skills": ["data-cleaning", "python"],
            "category": "development",
        },
        headers=h_pub,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]

    # NOTE: 另一个用户注册 3 个 Agent，其中一个已有完成记录
    exec_user = f"reccexe_{_unique()}"
    tk_exe = _register_user(exec_user, f"{exec_user}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    agent_ids = []
    for i in range(3):
        ar = client.post("/agents/register", json={"name": f"rec-agent-{i}", "description": "d"}, headers=h_exe)
        agent_ids.append(ar.json()["id"])

    # NOTE: 给其中一个 Agent 刷一条已完成历史
    from app.database.relational_db import SessionLocal, Task
    from datetime import datetime
    dbs = SessionLocal()
    try:
        t2 = Task(
            title="history",
            description="x",
            status="completed",
            priority="medium",
            task_type="general",
            owner_id=1,
            agent_id=agent_ids[0],
            reward_points=20,
            category="development",
            completed_at=datetime.utcnow(),
        )
        dbs.add(t2)
        dbs.commit()
    finally:
        dbs.close()

    r = client.get(f"/tasks/{task_id}/recommend-candidates?k=3", headers=h_pub)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["task_id"] == task_id
    assert len(data["candidates"]) <= 3
    assert data["total_evaluated"] >= 1
    # NOTE: 返回结构正确
    if data["candidates"]:
        top = data["candidates"][0]
        assert "reputation_score" in top
        assert "match" in top
        assert "suggested_price" in top
        assert top["suggested_price"] >= 1
        assert "breakdown" in top["match"]

    # NOTE: 非发布者访问 403
    other = f"reccoth_{_unique()}"
    tk_other = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    r2 = client.get(
        f"/tasks/{task_id}/recommend-candidates",
        headers={"Authorization": f"Bearer {tk_other}"},
    )
    assert r2.status_code == 403


def test_recommend_candidates_price_fit_dimension():
    """历史价位相近度：任务奖励与 Agent 历史中位价接近时 price_fit > 0。"""
    pub = f"recpf_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 200}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={
            "title": "price-fit-task",
            "reward_points": 100,
            "completion_webhook_url": "https://example.com/cb",
            "category": "development",
        },
        headers=h_pub,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]

    exec_user = f"recpfx_{_unique()}"
    tk_exe = _register_user(exec_user, f"{exec_user}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    near_agent = client.post("/agents/register", json={"name": "near-price", "description": "d"}, headers=h_exe).json()["id"]

    from app.database.relational_db import SessionLocal, Task
    from datetime import datetime

    dbs = SessionLocal()
    try:
        for _ in range(3):
            dbs.add(Task(
                title="hist", description="x", status="completed", priority="medium",
                task_type="general", owner_id=1, agent_id=near_agent,
                reward_points=100, category="development", completed_at=datetime.utcnow(),
            ))
        dbs.commit()
    finally:
        dbs.close()

    r = client.get(f"/tasks/{task_id}/recommend-candidates?k=10", headers=h_pub)
    assert r.status_code == 200, r.text
    cands = r.json()["candidates"]
    match = next((c for c in cands if c["agent"]["id"] == near_agent), None)
    assert match is not None, "near-price agent should be recommended"
    assert "price_fit" in match["match"]["breakdown"]
    assert match["match"]["breakdown"]["price_fit"] > 0
    assert match.get("agent_median_price") == 100


def test_invite_agent_makes_task_invitees_only():
    """发布方邀请 Agent 后任务默认隐藏，非邀请人看不到。"""
    pub = f"invp_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 30}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={"title": "定向任务", "reward_points": 5, "completion_webhook_url": "https://example.com/cb"},
        headers=h_pub,
    )
    task_id = tr.json()["id"]

    exe = f"invex_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    agent_id = client.post("/agents/register", json={"name": "invited", "description": "d"}, headers=h_exe).json()["id"]

    out = f"invout_{_unique()}"
    tk_out = _register_user(out, f"{out}@example.com", "pw")["access_token"]
    h_out = {"Authorization": f"Bearer {tk_out}"}

    # NOTE: 邀请前，外部用户可在 /tasks 看到
    before = client.get("/tasks", headers=h_out).json()
    assert any(x["id"] == task_id for x in before.get("tasks", []))

    # NOTE: 发布方邀请 exec 的 agent
    r = client.post(
        f"/tasks/{task_id}/invite-agent",
        json={"agent_id": agent_id},
        headers=h_pub,
    )
    assert r.status_code == 200, r.text
    assert r.json()["visibility"] == "invitees_only"
    assert agent_id in r.json()["invited_agent_ids"]

    # NOTE: 邀请后，无关用户在 /tasks 列表看不到该任务
    outsider_list = client.get("/tasks", headers=h_out).json()
    assert not any(x["id"] == task_id for x in outsider_list.get("tasks", []))
    # NOTE: 也不能直接访问详情
    det = client.get(f"/tasks/{task_id}", headers=h_out)
    assert det.status_code == 404

    # NOTE: 被邀请的 exec 用户可见
    det_ok = client.get(f"/tasks/{task_id}", headers=h_exe)
    assert det_ok.status_code == 200
    exec_list = client.get("/tasks", headers=h_exe).json()
    assert any(x["id"] == task_id for x in exec_list.get("tasks", []))

    # NOTE: 被邀请 Agent 可接取
    sub = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=h_exe)
    assert sub.status_code == 200, sub.text


def test_invite_agent_rejects_self_owned_agent():
    """发布方邀请自己 Agent -> 400。"""
    pub = f"invself_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 20}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={"title": "self", "reward_points": 2, "completion_webhook_url": "https://example.com/cb"},
        headers=h_pub,
    )
    task_id = tr.json()["id"]
    my_agent = client.post("/agents/register", json={"name": "mine", "description": "d"}, headers=h_pub).json()["id"]
    r = client.post(
        f"/tasks/{task_id}/invite-agent",
        json={"agent_id": my_agent},
        headers=h_pub,
    )
    assert r.status_code == 400


def test_recommend_candidates_excludes_owner_agents():
    """推荐结果不含发布者自己的 Agent。"""
    pub = f"recexcl_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 20}, headers=h_pub)
    my_agent = client.post("/agents/register", json={"name": "my-own", "description": "d"}, headers=h_pub).json()["id"]
    tr = client.post(
        "/tasks",
        json={"title": "excl", "reward_points": 3, "completion_webhook_url": "https://example.com/cb"},
        headers=h_pub,
    )
    task_id = tr.json()["id"]
    r = client.get(f"/tasks/{task_id}/recommend-candidates", headers=h_pub)
    assert r.status_code == 200
    cand_ids = [c["agent"]["id"] for c in r.json()["candidates"]]
    assert my_agent not in cand_ids


def test_cancel_task_only_owner():
    """仅发布者可撤单。"""
    owner = f"cown_{_unique()}"
    tk_owner = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h_owner = {"Authorization": f"Bearer {tk_owner}"}
    client.post("/account/recharge", json={"amount": 30}, headers=h_owner)
    r = client.post(
        "/tasks",
        json={
            "title": "他人任务",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h_owner,
    )
    task_id = r.json()["id"]
    other = f"cother_{_unique()}"
    tk_other = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    h_other = {"Authorization": f"Bearer {tk_other}"}
    rc = client.post(f"/tasks/{task_id}/cancel", headers=h_other)
    assert rc.status_code == 403


def test_task_radar_owner_only_and_returns_open_tasks():
    """任务雷达：仅 Agent 拥有者可访问；只返回自己未发布的开放任务。"""
    pub = f"rdrp_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 60}, headers=h_pub)
    for i in range(3):
        client.post(
            "/tasks",
            json={
                "title": f"radar-open-{i}",
                "reward_points": 2,
                "category": "development",
                "completion_webhook_url": "https://example.com/cb",
            },
            headers=h_pub,
        )

    exe = f"rdrex_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    agent_id = client.post(
        "/agents/register",
        json={"name": "radar-agent", "description": "dev"},
        headers=h_exe,
    ).json()["id"]

    r = client.get(f"/agents/{agent_id}/task-radar?k=5", headers=h_exe)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent_id"] == agent_id
    assert "weights" in data and abs(sum(data["weights"].values()) - 1.0) < 1e-6
    assert isinstance(data["radar"], list)
    exe_uid = _user_id_of(tk_exe)
    for item in data["radar"]:
        assert "score" in item and 0 <= item["score"] <= 100
        assert "breakdown" in item
        assert "suggested_bid" in item
        assert item["task"]["owner_id"] != exe_uid, "不会撮合自己发布的任务"
        assert item["task"]["visibility"] in ("public", "invitees_only")

    stranger = f"rdrst_{_unique()}"
    tk_st = _register_user(stranger, f"{stranger}@example.com", "pw")["access_token"]
    h_st = {"Authorization": f"Bearer {tk_st}"}
    rf = client.get(f"/agents/{agent_id}/task-radar", headers=h_st)
    assert rf.status_code == 403


def _user_id_of(token: str, prefer=None):
    """工具：解析 access_token 对应的 user_id（/account/me）。失败时返回 prefer。"""
    h = {"Authorization": f"Bearer {token}"}
    r = client.get("/account/me", headers=h)
    if r.status_code != 200:
        return prefer
    return r.json().get("user_id", prefer)


def test_task_radar_includes_invited_tasks_with_boost():
    """定向任务被邀请 Agent 时出现在该 Agent 的雷达内并有优先权。"""
    pub = f"rdrinv_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 40}, headers=h_pub)
    tr = client.post(
        "/tasks",
        json={
            "title": "radar-invited-only",
            "reward_points": 4,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h_pub,
    )
    task_id = tr.json()["id"]

    exe = f"rdrinvex_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    agent_id = client.post(
        "/agents/register",
        json={"name": "invited-radar-agent", "description": "d"},
        headers=h_exe,
    ).json()["id"]

    r_inv = client.post(
        f"/tasks/{task_id}/invite-agent",
        json={"agent_id": agent_id},
        headers=h_pub,
    )
    assert r_inv.status_code == 200, r_inv.text

    r = client.get(f"/agents/{agent_id}/task-radar?k=20", headers=h_exe)
    assert r.status_code == 200, r.text
    radar = r.json()["radar"]
    assert any(item["task"]["id"] == task_id for item in radar), "定向任务应该出现在被邀请 Agent 的雷达中"

    other = f"rdrinvo_{_unique()}"
    tk_other = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    h_other = {"Authorization": f"Bearer {tk_other}"}
    other_agent = client.post(
        "/agents/register",
        json={"name": "outsider", "description": "d"},
        headers=h_other,
    ).json()["id"]
    r2 = client.get(f"/agents/{other_agent}/task-radar?k=50", headers=h_other)
    assert r2.status_code == 200
    ids = [it["task"]["id"] for it in r2.json()["radar"]]
    assert task_id not in ids, "非被邀请 Agent 的雷达不应看到定向任务"


def test_tasks_estimate_public_fallback_for_empty_category():
    """价格/SLA 预估：未知类目走启发式回退，仍给出合理默认值。"""
    r = client.get(
        "/tasks/estimate",
        params={"category": f"nonexistent_{_unique()}", "difficulty": "normal"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["heuristic_used"] is True
    assert data["sample_size"] == 0
    rp = data["reward_points"]
    assert rp["suggested"] >= 1
    assert rp["p25"] <= rp["p50"] <= rp["p75"] <= rp["p90"]
    assert data["confidence"] == "low"


def test_tasks_estimate_difficulty_multiplier():
    """难度乘数生效：expert 应 > easy。"""
    r_easy = client.get("/tasks/estimate", params={"category": "development", "difficulty": "easy"})
    r_expert = client.get("/tasks/estimate", params={"category": "development", "difficulty": "expert"})
    assert r_easy.status_code == 200 and r_expert.status_code == 200
    assert r_expert.json()["reward_points"]["p50"] > r_easy.json()["reward_points"]["p50"]


def test_tasks_estimate_uses_history_when_samples_sufficient():
    """有 >=5 条相似任务时应切换到历史聚合，sample_size>0 且 heuristic_used=False。"""
    from app.services.price_sla_estimator import clear_estimate_cache
    clear_estimate_cache()

    pub = f"estpub_{_unique()}"
    tk = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post("/account/recharge", json={"amount": 200}, headers=h)

    uniq_cat = f"est_{_unique()}"
    for i in range(6):
        client.post(
            "/tasks",
            json={
                "title": f"est-{i}",
                "reward_points": 10 + i,
                "category": uniq_cat,
                "completion_webhook_url": "https://example.com/cb",
            },
            headers=h,
        )
    r = client.get("/tasks/estimate", params={"category": uniq_cat})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sample_size"] >= 5
    assert data["heuristic_used"] is False
    assert data["confidence"] in ("medium", "high")


def test_intent_to_task_heuristic_parses_skill_and_deadline():
    """Intent-to-Task：启发式识别技能、难度、期限、预算。"""
    user = f"intent_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r = client.post(
        "/tasks/draft-from-intent",
        json={"intent": "紧急修复登录接口的 bug，3 天内完成，预算 20 点"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["skill"] == "bug_fix"
    assert data["category"] == "development"
    assert data["difficulty"] == "hard"
    assert data["deadline_days"] == 3
    assert data["reward_hint"] == 20
    assert data["draft_source"] == "intent"
    assert data["source"] in ("heuristic", "llm")
    assert data["title"]
    assert "验收标准" in data["description"] or "acceptance" in data["description"].lower()
    assert len(data["acceptance_criteria"]) >= 2


def test_intent_to_task_requires_auth_and_validates_empty():
    """Intent-to-Task：未登录 401；空 intent 400。"""
    r = client.post("/tasks/draft-from-intent", json={"intent": "hi"})
    assert r.status_code in (401, 403)

    user = f"intempty_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r2 = client.post("/tasks/draft-from-intent", json={"intent": "   "}, headers=h)
    assert r2.status_code == 400


def test_intent_to_task_rate_limit(monkeypatch):
    """Intent-to-Task：超限返回 429。"""
    from app.domain import task_helpers as th
    th.intent_rate_bucket.clear()
    monkeypatch.setenv("CLAWJOB_INTENT_RATE_PER_HOUR", "2")

    original = th.INTENT_RATE_LIMIT_MAX
    th.INTENT_RATE_LIMIT_MAX = 2
    try:
        user = f"intrl_{_unique()}"
        tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
        h = {"Authorization": f"Bearer {tk}"}
        for _ in range(2):
            r = client.post("/tasks/draft-from-intent", json={"intent": "写一篇博客"}, headers=h)
            assert r.status_code == 200, r.text
        r_over = client.post("/tasks/draft-from-intent", json={"intent": "写一篇博客"}, headers=h)
        assert r_over.status_code == 429
        assert "Retry-After" in r_over.headers
    finally:
        th.INTENT_RATE_LIMIT_MAX = original
        th.intent_rate_bucket.clear()


def test_task_radar_custom_weights_normalized():
    """雷达权重可调：传入后端会归一化。"""
    exe = f"rdrw_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    agent_id = client.post(
        "/agents/register",
        json={"name": "weighted-radar", "description": "d"},
        headers=h_exe,
    ).json()["id"]

    r = client.get(
        f"/agents/{agent_id}/task-radar",
        params={"k": 5, "w_skill": 2, "w_reward": 1, "w_fresh": 1, "w_history": 0},
        headers=h_exe,
    )
    assert r.status_code == 200
    w = r.json()["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-6
    assert w["skill_match"] > w["reward_fit"]
    assert w["history_affinity"] == 0.0


# ========================= B-4 反向竞标（Reverse Auction） =========================

def _publish_auction_task(token: str, *, max_reward: int = 50, min_reward: int = 5, deadline: Optional[str] = None) -> int:
    h = {"Authorization": f"Bearer {token}"}
    body = {
        "title": "auction-task",
        "reward_points": max_reward,
        "completion_webhook_url": "https://example.com/cb",
        "category": "development",
        "auction": {
            "enabled": True,
            "min_reward": min_reward,
            "deadline": deadline,
            "auto_pick": "manual",
        },
    }
    r = client.post("/tasks", json=body, headers=h)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_auction_publish_and_bid_roundtrip():
    """反向竞标：发布 → Agent 报价 → 发布方选标，完成差价退款与任务分配。"""
    pub = f"ap_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    r_rc = client.post("/account/recharge", json={"amount": 100}, headers=h_pub)
    assert r_rc.status_code == 200
    task_id = _publish_auction_task(tk_pub, max_reward=50, min_reward=5)

    # 发布后 credits 应该扣了 50 作为上限预算
    me_pub = client.get("/account/me", headers=h_pub).json()
    assert me_pub["credits"] == 100 - 50

    # Bidder 1
    exe = f"ax_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    ag1 = client.post("/agents/register", json={"name": "bidder-1", "description": "d"}, headers=h_exe).json()["id"]
    rb1 = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag1, "price": 30, "eta_hours": 6, "proposal": "方案 A"}, headers=h_exe)
    assert rb1.status_code == 200, rb1.text
    assert rb1.json()["bid"]["price"] == 30

    # Bidder 2
    exe2 = f"ay_{_unique()}"
    tk_exe2 = _register_user(exe2, f"{exe2}@example.com", "pw")["access_token"]
    h_exe2 = {"Authorization": f"Bearer {tk_exe2}"}
    ag2 = client.post("/agents/register", json={"name": "bidder-2", "description": "d"}, headers=h_exe2).json()["id"]
    rb2 = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag2, "price": 25, "eta_hours": 4, "proposal": "方案 B"}, headers=h_exe2)
    assert rb2.status_code == 200, rb2.text
    bid2_id = rb2.json()["bid"]["id"]

    # 发布方列表能看到全部报价
    rl = client.get(f"/tasks/{task_id}/bids", headers=h_pub)
    assert rl.status_code == 200
    assert rl.json()["is_publisher"] is True
    assert len(rl.json()["bids"]) == 2

    # Bidder 1 只能看到自己的
    rl1 = client.get(f"/tasks/{task_id}/bids", headers=h_exe)
    assert rl1.status_code == 200
    assert all(b["agent_id"] == ag1 for b in rl1.json()["bids"])

    # 竞标期间不能订阅
    r_sub = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag1}, headers=h_exe)
    assert r_sub.status_code == 400

    # 发布方选 bidder 2
    r_ac = client.post(f"/tasks/{task_id}/bids/{bid2_id}/accept", headers=h_pub)
    assert r_ac.status_code == 200, r_ac.text
    data = r_ac.json()
    assert data["final_reward_points"] == 25
    assert data["refunded_points"] == 25
    assert data["agent_id"] == ag2

    # 发布方 credits 应已退回 25
    me_pub2 = client.get("/account/me", headers=h_pub).json()
    assert me_pub2["credits"] == (100 - 50) + 25

    # 任务详情显示 auction.awarded，agent_id=ag2
    td = client.get(f"/tasks/{task_id}").json()
    assert td["agent_id"] == ag2
    assert td["reward_points"] == 25
    assert td["auction"]["status"] == "awarded"
    assert td["auction"]["selected_bid_id"] == bid2_id


def test_auction_bid_validation_rules():
    """竞标报价需在 [min, max] 内；发布方不可对自己任务报价。"""
    pub = f"av_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h_pub)
    task_id = _publish_auction_task(tk_pub, max_reward=40, min_reward=10)

    # 发布方自己用自己的 Agent 报价应 400
    pub_agent = client.post("/agents/register", json={"name": "me-agent", "description": "d"}, headers=h_pub).json()["id"]
    r_self = client.post(f"/tasks/{task_id}/bids", json={"agent_id": pub_agent, "price": 20}, headers=h_pub)
    assert r_self.status_code == 400

    # 另一个用户
    exe = f"avx_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    ag = client.post("/agents/register", json={"name": "bidder", "description": "d"}, headers=h_exe).json()["id"]

    # 高于上限
    r_hi = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag, "price": 50}, headers=h_exe)
    assert r_hi.status_code == 400

    # 低于底价
    r_lo = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag, "price": 5}, headers=h_exe)
    assert r_lo.status_code == 400

    # 合法报价
    r_ok = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag, "price": 25}, headers=h_exe)
    assert r_ok.status_code == 200


def test_auction_withdraw_and_close_no_bids():
    """撤回自己的报价；无成交关闭竞标应全额退款并取消任务。"""
    pub = f"aw_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 60}, headers=h_pub)

    task_id = _publish_auction_task(tk_pub, max_reward=30)
    exe = f"awx_{_unique()}"
    tk_exe = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_exe = {"Authorization": f"Bearer {tk_exe}"}
    ag = client.post("/agents/register", json={"name": "b", "description": "d"}, headers=h_exe).json()["id"]
    rb = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag, "price": 20}, headers=h_exe)
    bid_id = rb.json()["bid"]["id"]

    # 非本人撤回 403
    other = f"awo_{_unique()}"
    tk_other = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    h_other = {"Authorization": f"Bearer {tk_other}"}
    r_forbid = client.post(f"/tasks/{task_id}/bids/{bid_id}/withdraw", headers=h_other)
    assert r_forbid.status_code == 403

    # 本人撤回成功
    r_ok = client.post(f"/tasks/{task_id}/bids/{bid_id}/withdraw", headers=h_exe)
    assert r_ok.status_code == 200
    assert r_ok.json()["bid"]["status"] == "withdrawn"

    # 发布方关闭竞标：无 active 报价 → 全额退款 + 取消
    me_before = client.get("/account/me", headers=h_pub).json()["credits"]
    r_close = client.post(f"/tasks/{task_id}/bids/close", headers=h_pub)
    assert r_close.status_code == 200, r_close.text
    assert r_close.json()["awarded"] is False
    assert r_close.json()["refunded_points"] == 30
    me_after = client.get("/account/me", headers=h_pub).json()["credits"]
    assert me_after == me_before + 30
    td = client.get(f"/tasks/{task_id}").json()
    assert td["status"] == "cancelled_refunded"
    assert td["auction"]["status"] == "cancelled"


def test_auction_close_auto_pick_lowest_price():
    """auto_pick=lowest_price：关闭时若有 active 报价，自动选最低价。"""
    pub = f"al_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 200}, headers=h_pub)

    body = {
        "title": "auto-pick-auction",
        "reward_points": 80,
        "completion_webhook_url": "https://example.com/cb",
        "auction": {"enabled": True, "min_reward": 10, "auto_pick": "lowest_price"},
    }
    task_id = client.post("/tasks", json=body, headers=h_pub).json()["id"]

    # 两个出价
    for i, price in enumerate([60, 35]):
        u = f"aln_{i}_{_unique()}"
        tk = _register_user(u, f"{u}@example.com", "pw")["access_token"]
        h = {"Authorization": f"Bearer {tk}"}
        ag = client.post("/agents/register", json={"name": f"bidder-{i}", "description": "d"}, headers=h).json()["id"]
        rb = client.post(f"/tasks/{task_id}/bids", json={"agent_id": ag, "price": price}, headers=h)
        assert rb.status_code == 200, rb.text

    r_close = client.post(f"/tasks/{task_id}/bids/close", headers=h_pub, json={"auto_pick_if_bids": True})
    assert r_close.status_code == 200
    data = r_close.json()
    assert data["awarded"] is True
    assert data["final_reward_points"] == 35  # 自动选最低
    assert data["refunded_points"] == 45  # 80 - 35


# ========================= D-5 邀请返点 =========================

def test_referral_bonus_on_first_task_reward(monkeypatch):
    """邀请码绑定 + 被邀请人首单完成 → 双方获得返点；幂等保证只发一次。"""
    monkeypatch.setenv("REFERRAL_BONUS_REFERRER", "100")
    monkeypatch.setenv("REFERRAL_BONUS_INVITEE", "50")

    # referrer 注册并获取邀请码
    ref = f"refer_{_unique()}"
    tk_ref = _register_user(ref, f"{ref}@example.com", "pw")["access_token"]
    h_ref = {"Authorization": f"Bearer {tk_ref}"}
    my = client.get("/account/referral", headers=h_ref).json()
    code = my["referral_code"]
    assert len(code) >= 6

    # invitee 使用 referral_code 注册
    inv = f"invit_{_unique()}"
    r = client.post("/auth/send-verification-code", json={"email": f"{inv}@example.com"})
    assert r.status_code == 200
    r2 = client.post("/auth/register", json={
        "username": inv,
        "email": f"{inv}@example.com",
        "password": "pw",
        "verification_code": os.environ.get("VERIFICATION_CODE_DEV", "123456"),
        "referral_code": code,
    })
    assert r2.status_code == 200
    data = r2.json()
    assert data.get("referral_bound") is True
    tk_inv = data["access_token"]
    h_inv = {"Authorization": f"Bearer {tk_inv}"}

    # invitee 接取一个任务并完成 → 发放 task_reward
    pub = f"rfpub_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 50}, headers=h_pub)
    rtask = client.post("/tasks", json={
        "title": "referral-trigger",
        "reward_points": 20,
        "completion_webhook_url": "https://example.com/cb",
    }, headers=h_pub)
    assert rtask.status_code == 200
    task_id = rtask.json()["id"]

    # invitee 用自己的 Agent 接取任务
    ag = client.post("/agents/register", json={"name": "ref-agent", "description": "d"}, headers=h_inv).json()["id"]
    rs = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag}, headers=h_inv)
    assert rs.status_code == 200, rs.text
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        rsub = client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "done"}, headers=h_inv)
        assert rsub.status_code == 200, rsub.text
    rconfirm = client.post(f"/tasks/{task_id}/confirm", json={"verification_mode": "manual_review"}, headers=h_pub)
    assert rconfirm.status_code == 200, rconfirm.text

    # referrer 应到账 100
    me_ref = client.get("/account/me", headers=h_ref).json()
    assert me_ref["credits"] >= 100, me_ref

    # invitee 奖励 = 任务分成 + 返点 50
    me_inv = client.get("/account/me", headers=h_inv).json()
    # 任务 20 * (1 - commission) + 返点 50
    assert me_inv["credits"] >= 50 + 19

    # 记录：referrer 的 /account/referral 应显示已完成 1
    summary = client.get("/account/referral", headers=h_ref).json()
    assert summary["completed_first_task"] == 1
    assert summary["total_reward_points"] >= 100

    records = client.get("/account/referral/records", headers=h_ref).json()
    assert records["total"] == 1
    assert records["records"][0]["status"] == "rewarded"


def test_referral_invalid_code_ignored():
    """非法邀请码：注册仍然成功，不绑定；返回 referral_bound=False。"""
    inv = f"badref_{_unique()}"
    r = client.post("/auth/send-verification-code", json={"email": f"{inv}@example.com"})
    assert r.status_code == 200
    r2 = client.post("/auth/register", json={
        "username": inv,
        "email": f"{inv}@example.com",
        "password": "pw",
        "verification_code": os.environ.get("VERIFICATION_CODE_DEV", "123456"),
        "referral_code": "NOTEXIST9999",
    })
    assert r2.status_code == 200
    assert r2.json().get("referral_bound") is False


# ========================= C-6 审计日志导出 =========================

def _make_admin_token(username: str) -> str:
    tk = _register_user(username, f"{username}@example.com", "adminpw")["access_token"]
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == username).first()
        u.is_superuser = True
        db.commit()
    finally:
        db.close()
    return tk


def test_audit_export_zip_superuser_only():
    """C-6：审计日志导出 ZIP。
    - 普通用户访问 403
    - 超管访问 200，返回 ZIP 且包含 manifest.json 与三类 CSV
    """
    import io
    import zipfile
    normal = f"audnorm_{_unique()}"
    tk_n = _register_user(normal, f"{normal}@example.com", "pw")["access_token"]
    r_forbid = client.get("/admin/audit/export", headers={"Authorization": f"Bearer {tk_n}"})
    assert r_forbid.status_code == 403

    admin = f"admaud_{_unique()}"
    tk_a = _make_admin_token(admin)
    h_a = {"Authorization": f"Bearer {tk_a}"}

    # 先制造一些数据
    client.post("/account/recharge", json={"amount": 50}, headers=h_a)
    client.post(
        "/tasks",
        json={
            "title": "audit-export-sample",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h_a,
    )

    r = client.get("/admin/audit/export", headers=h_a)
    assert r.status_code == 200, r.text
    assert r.headers.get("content-type", "").startswith("application/zip")
    disp = r.headers.get("content-disposition", "")
    assert "clawjob-audit-" in disp

    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names
        assert "system_logs.csv" in names
        assert "credit_transactions.csv" in names
        assert "tasks.csv" in names
        mf = __import__("json").loads(zf.read("manifest.json").decode("utf-8"))
        assert "datasets" in mf and set(mf["datasets"].keys()) >= {"system_logs", "credit_transactions", "tasks"}
        assert mf["range"]["start"] < mf["range"]["end"]
        # tasks.csv 至少包含表头 + 1 行
        tasks_lines = zf.read("tasks.csv").decode("utf-8").strip().splitlines()
        assert len(tasks_lines) >= 2


def test_audit_export_rejects_invalid_range():
    admin = f"admrg_{_unique()}"
    tk_a = _make_admin_token(admin)
    h_a = {"Authorization": f"Bearer {tk_a}"}
    r = client.get("/admin/audit/export?start=2026-05-01T00:00:00Z&end=2026-04-01T00:00:00Z", headers=h_a)
    assert r.status_code == 400


# ========================= D-4 Agent 公开主页 =========================

def test_public_user_profile_by_username():
    """D-4：/u/{username} 返回公开资料 + Agents 汇总，不泄露敏感字段。"""
    u = f"pubu_{_unique()}"
    tk = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r1 = client.post("/agents/register", json={"name": "pub-agent", "description": "d"}, headers=h)
    assert r1.status_code == 200, r1.text
    r2 = client.post("/agents/register", json={"name": "pub-agent-2", "description": "d"}, headers=h)
    assert r2.status_code == 200, r2.text

    r = client.get(f"/u/{u}")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["username"] == u
    assert data["summary"]["agents_count"] == 2
    assert "credits" not in data
    assert "email" not in data
    assert all("reputation_score" in a for a in data["agents"])

    r2 = client.get("/u/does-not-exist-" + _unique())
    assert r2.status_code == 404


def test_agent_case_studies_public():
    """D-4：/agents/{id}/cases 返回 status=completed 的公开案例。"""
    # 制造一个完成任务
    pub = f"casespub_{_unique()}"
    tk_pub = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h_pub = {"Authorization": f"Bearer {tk_pub}"}
    client.post("/account/recharge", json={"amount": 50}, headers=h_pub)
    rt = client.post(
        "/tasks",
        json={"title": "case-study-task", "reward_points": 5, "completion_webhook_url": "https://example.com/cb"},
        headers=h_pub,
    )
    task_id = rt.json()["id"]

    exe = f"casesex_{_unique()}"
    tk_ex = _register_user(exe, f"{exe}@example.com", "pw")["access_token"]
    h_ex = {"Authorization": f"Bearer {tk_ex}"}
    ag = client.post("/agents/register", json={"name": "caseagent", "description": "d"}, headers=h_ex).json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": ag}, headers=h_ex)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "outcome ok"}, headers=h_ex)
    client.post(f"/tasks/{task_id}/confirm", headers=h_pub)

    r = client.get(f"/agents/{ag}/cases")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["agent_id"] == ag
    assert data["total"] >= 1
    assert any(c["task_id"] == task_id for c in data["cases"])


# ========================= C-13 内容安全 / PII 网关 =========================


def test_safety_blocks_blacklisted_publish(monkeypatch):
    """C-13：publish_task 对黑名单关键词阻断，写 safety_events。"""
    from app.services import safety_pipeline as _sf

    monkeypatch.setenv("SAFETY_BLACKLIST", "contraband_xyz")
    u = f"safe_{_unique()}"
    tk = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r = client.post(
        "/tasks",
        json={
            "title": "ok-title",
            "description": "please deliver contraband_xyz to me",
        },
        headers=h,
    )
    assert r.status_code == 400
    assert "内容安全" in r.text

    tk_a = _make_admin_token(f"safeadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    rs = client.get("/admin/safety/events", params={"action": "block"}, headers=h_a)
    assert rs.status_code == 200, rs.text
    items = rs.json()["items"]
    assert any("blacklist:contraband_xyz" in (it.get("reasons") or []) for it in items)


def test_safety_redacts_pii_in_message():
    """C-13：站内信内容中的邮箱/手机号被脱敏。"""
    sender = f"sndr_{_unique()}"
    recv = f"rcvr_{_unique()}"
    tk_s = _register_user(sender, f"{sender}@example.com", "pw")["access_token"]
    _register_user(recv, f"{recv}@example.com", "pw")
    h_s = {"Authorization": f"Bearer {tk_s}"}

    r = client.post(
        "/messages",
        json={
            "recipient_username": recv,
            "title": "hi",
            "content": "contact me at foo@bar.com or +1 415 555 1212 anytime",
        },
        headers=h_s,
    )
    assert r.status_code == 200, r.text
    msg_id = r.json()["id"]

    from app.database.relational_db import SessionLocal, InternalMessage
    db = SessionLocal()
    try:
        row = db.query(InternalMessage).filter(InternalMessage.id == msg_id).first()
        assert row is not None
        assert "foo@bar.com" not in row.content
        assert "[redacted-email]" in row.content
    finally:
        db.close()


def test_safety_stats_admin():
    """C-13：/admin/safety/stats 返回 by_action / by_source 汇总。"""
    tk_a = _make_admin_token(f"sfstat_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    r = client.get("/admin/safety/stats", headers=h_a)
    assert r.status_code == 200, r.text
    data = r.json()
    assert "by_action" in data and "by_source" in data
    assert "total" in data


# ========================= C-12 执行沙箱 cost cap =========================


def test_execute_respects_duration_quota():
    """C-12：当执行超出 duration cap 时返回 429 并写 last_execute.quota_exceeded。"""
    pub = f"sbxpub_{_unique()}"
    tk = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}

    r = client.post(
        "/tasks",
        json={"title": "sandbox-task", "description": "quota test"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    # 强制超时：把任务 input_data.execution_quota.max_duration_seconds 设为 1，
    # 并 mock task_system.execute_task 睡眠 3 秒
    from app.database.relational_db import SessionLocal, Task as TaskModel
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        data = dict(t.input_data or {})
        data["execution_quota"] = {"max_duration_seconds": 1}
        t.input_data = data
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(t, "input_data")
        db.commit()
    finally:
        db.close()

    import asyncio as _asyncio
    async def slow_exec(tid):
        await _asyncio.sleep(3)
        return {"ok": True}

    with patch("app.main.task_system.execute_task", side_effect=slow_exec):
        r = client.post(f"/tasks/{task_id}/execute", headers=h)
    assert r.status_code == 429, r.text
    assert "quota_exceeded" in r.text or "沙箱" in r.text


# ========================= C-11 步骤级执行回放 =========================


def test_execution_runs_and_step_replay():
    """C-11：execute 后 /tasks/{id}/runs 与 /tasks/{id}/runs/{run_id}/steps 可读。"""
    pub = f"runpub_{_unique()}"
    tk = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r = client.post(
        "/tasks",
        json={"title": "run-replay-task", "description": "hello"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["id"]

    async def ok_exec(tid):
        return {"ok": True, "output": "done"}

    with patch("app.main.task_system.execute_task", side_effect=ok_exec):
        r = client.post(f"/tasks/{task_id}/execute", headers=h)
    assert r.status_code == 200, r.text
    body = r.json()
    run_id = body.get("run_id")
    assert isinstance(run_id, str) and len(run_id) > 0

    runs = client.get(f"/tasks/{task_id}/runs", headers=h).json()
    assert any(x["run_id"] == run_id and x["ok"] for x in runs["items"])

    steps = client.get(f"/tasks/{task_id}/runs/{run_id}/steps", headers=h).json()
    kinds = [s["kind"] for s in steps["steps"]]
    assert "start" in kinds and "end" in kinds
    assert any(k in ("tool", "output") for k in kinds)

    exp = client.get(f"/tasks/{task_id}/runs/{run_id}/export", headers=h)
    assert exp.status_code == 200
    doc = exp.json()
    assert doc["task_id"] == task_id
    assert doc["run"]["run_id"] == run_id


def test_execution_runs_forbidden_to_stranger():
    """C-11：非任务发布方/接取方（非超管）不能读取 runs。"""
    pub = f"runpub2_{_unique()}"
    other = f"other_{_unique()}"
    tk = _register_user(pub, f"{pub}@example.com", "pw")["access_token"]
    tk_o = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    h_o = {"Authorization": f"Bearer {tk_o}"}
    r = client.post("/tasks", json={"title": "priv-run", "description": "x"}, headers=h)
    task_id = r.json()["id"]
    r = client.get(f"/tasks/{task_id}/runs", headers=h_o)
    assert r.status_code == 403


# ========================= D-22 Insights 报表 =========================


def test_publisher_insights_self_service():
    """D-22：/account/insights 返回 spent / tasks / spending_by_category 等。"""
    u = f"insp_{_unique()}"
    tk = _register_user(u, f"{u}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h)
    client.post(
        "/tasks",
        json={
            "title": "insight-task-1",
            "category": "data-clean",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h,
    )
    client.post(
        "/tasks",
        json={
            "title": "insight-task-2",
            "category": "data-clean",
            "reward_points": 7,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=h,
    )
    r = client.get("/account/insights", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["tasks"]["total"] >= 2
    assert data["spent_points"] >= 12
    assert data["spending_by_category"].get("data-clean", 0) >= 12


def test_platform_insights_admin():
    """D-22：/admin/insights/platform 返回 GMV / funnel / daily / retention。"""
    tk_a = _make_admin_token(f"insadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    r = client.get("/admin/insights/platform", headers=h_a)
    assert r.status_code == 200, r.text
    data = r.json()
    for key in ("gmv", "revenue", "funnel", "daily", "retention"):
        assert key in data
    assert "funnel" in data and "published" in data["funnel"]


# ========================= C-14 KYC / KYB + 提现闸门 =========================


def test_kyc_personal_submit_and_approve_unblocks_withdrawal():
    """C-14：个人 KYC 提交 → 默认 pending → 管理员通过 → 用户提现解锁。"""
    user = f"kyc_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    me = client.get("/account/kyc", headers=h).json()
    assert me["kyc_status"] == "none"
    # 未通过 KYC 时直接申请提现 -> 403
    r0 = client.post("/account/withdrawals", json={"amount": 50}, headers=h)
    assert r0.status_code == 403
    sub = client.post(
        "/account/kyc/personal",
        json={
            "legal_name": "Alice Chen",
            "id_type": "id_card",
            "id_number": "11010119900307XXXX",
            "country": "CN",
        },
        headers=h,
    )
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["kyc_status"] == "pending"
    rec_id = body["kyc"]["id"]
    # 明文不会回传，且密文已脱敏
    assert body["kyc"]["id_number_masked"].endswith("XX")
    # 管理员通过
    tk_a = _make_admin_token(f"kycadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    rev = client.post(f"/admin/kyc/records/{rec_id}/approve", json={}, headers=h_a)
    assert rev.status_code == 200, rev.text
    assert rev.json()["status"] == "approved"
    me2 = client.get("/account/kyc", headers=h).json()
    assert me2["kyc_status"] == "approved"


def test_payout_eligibility_reflects_credits_and_kyc():
    """提现资格：任务奖励在 credits，KYC + 收款账户决定 blockers。"""
    user = f"payel_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r0 = client.get("/account/payout-eligibility", headers=h)
    assert r0.status_code == 200, r0.text
    body = r0.json()
    assert "withdrawable_balance" in body
    assert "kyc_required" in body.get("blockers", [])
    assert body["eligible"] is False
    from app.database.relational_db import SessionLocal, User as UserModel

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        u.credits = 150
        u.kyc_status = "approved"
        u.receiving_account_type = "alipay"
        u.receiving_account_name = "Test"
        u.receiving_account_number = "***@a.com"
        db.commit()
    finally:
        db.close()
    r1 = client.get("/account/payout-eligibility", headers=h)
    assert r1.status_code == 200
    b1 = r1.json()
    assert b1["eligible"] is True
    assert b1["withdrawable_balance"] == 150


def test_withdraw_request_alias_matches_withdrawals():
    user = f"wdalias_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    from app.database.relational_db import SessionLocal, User as UserModel

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        u.credits = 80
        u.kyc_status = "approved"
        u.receiving_account_type = "alipay"
        u.receiving_account_name = "T"
        u.receiving_account_number = "***@a.com"
        db.commit()
    finally:
        db.close()
    sub = client.post("/account/withdraw/request", json={"amount": 50}, headers=h)
    assert sub.status_code == 200, sub.text
    assert sub.json()["status"] == "pending"


def test_kyc_reject_blocks_withdrawal_and_records_reason():
    """C-14：管理员驳回后，用户 kyc_status=rejected，仍无法提现。"""
    user = f"kycr_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    sub = client.post(
        "/account/kyc/personal",
        json={"legal_name": "X", "id_type": "passport", "id_number": "P11112222"},
        headers=h,
    )
    rec_id = sub.json()["kyc"]["id"]
    tk_a = _make_admin_token(f"kycadmr_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    rj = client.post(
        f"/admin/kyc/records/{rec_id}/reject",
        json={"reason": "证件照模糊"},
        headers=h_a,
    )
    assert rj.status_code == 200
    assert rj.json()["status"] == "rejected"
    me = client.get("/account/kyc", headers=h).json()
    assert me["kyc_status"] == "rejected"
    r = client.post("/account/withdrawals", json={"amount": 50}, headers=h)
    assert r.status_code == 403


def test_kyc_sandbox_skip_when_enabled(monkeypatch):
    """C-14：KYC_SANDBOX_MODE=1 时可沙盒跳过并解锁提现闸门。"""
    monkeypatch.setenv("KYC_SANDBOX_MODE", "1")
    user = f"kybsb_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    r = client.post("/account/kyc/sandbox-skip", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["kyc_status"] == "approved"
    me = client.get("/account/kyc", headers=h).json()
    assert me["kyc_status"] == "approved"
    monkeypatch.delenv("KYC_SANDBOX_MODE", raising=False)
    user2 = f"kybsb2_{_unique()}"
    tk2 = _register_user(user2, f"{user2}@example.com", "pw")["access_token"]
    h2 = {"Authorization": f"Bearer {tk2}"}
    r2 = client.post("/account/kyc/sandbox-skip", headers=h2)
    assert r2.status_code == 403


def test_kyc_admin_export_csv():
    """C-14：管理员可导出 KYC 记录 CSV。"""
    user = f"kycex_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post(
        "/account/kyc/personal",
        json={"legal_name": "Export Me", "id_type": "id_card", "id_number": "110101199001011234"},
        headers=h,
    )
    tk_a = _make_admin_token(f"kycexadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    r = client.get("/admin/kyc/export", params={"status": "pending"}, headers=h_a)
    assert r.status_code == 200, r.text
    assert "text/csv" in (r.headers.get("content-type") or "")
    body = r.content.decode("utf-8")
    assert "legal_name" in body
    assert "Export Me" in body


def test_runtime_circuit_breaker_config_patch():
    """熔断告警阈值：管理员可读取并更新 threshold / open_seconds。"""
    tk_a = _make_admin_token(f"cbcfg_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    g0 = client.get("/runtime/circuit-breakers/config", headers=h_a)
    assert g0.status_code == 200, g0.text
    p = client.patch(
        "/runtime/circuit-breakers/config",
        json={"threshold": 5, "open_seconds": 90},
        headers=h_a,
    )
    assert p.status_code == 200, p.text
    assert p.json()["threshold"] == 5
    assert p.json()["open_seconds"] == 90
    snap = client.get("/runtime/circuit-breakers", headers=h_a).json()
    assert snap["threshold"] == 5
    u2 = f"cbcfgu_{_unique()}"
    tk_u = _register_user(u2, f"{u2}@example.com", "pw")["access_token"]
    forbidden = client.patch(
        "/runtime/circuit-breakers/config",
        json={"threshold": 2},
        headers={"Authorization": f"Bearer {tk_u}"},
    )
    assert forbidden.status_code == 403


def test_kyc_business_submit_and_admin_list_filter():
    """C-14：企业 KYB 提交 + 管理员列表过滤。"""
    user = f"kyb_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    sub = client.post(
        "/account/kyc/business",
        json={
            "business_name": "ACME 工坊有限公司",
            "business_id": "91110108MA01234567",
            "legal_name": "Bob Wang",
            "country": "CN",
            "contact_email": "ops@acme.example.com",
        },
        headers=h,
    )
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["kyc"]["kind"] == "business"
    tk_a = _make_admin_token(f"kybadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    lst = client.get("/admin/kyc/records", params={"kind": "business", "status": "pending"}, headers=h_a)
    assert lst.status_code == 200
    assert lst.json()["total"] >= 1


def test_withdrawal_after_approval_deducts_commission_and_admin_can_pay():
    """C-14：通过 KYC + 有佣金余额 → 申请提现 → 管理员标记已打款。"""
    user = f"wdraw_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    # 给用户加佣金余额（模拟历史佣金到账）
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        u.credits = 200
        u.kyc_status = "approved"
        u.receiving_account_type = "alipay"
        u.receiving_account_name = "Test"
        u.receiving_account_number = "***@a.com"
        db.commit()
    finally:
        db.close()
    sub = client.post("/account/withdrawals", json={"amount": 80}, headers=h)
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["status"] == "pending"
    assert body["withdrawable_balance"] == 120
    # 管理员标记已打款
    tk_a = _make_admin_token(f"wdrawadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    decide = client.post(
        f"/admin/withdrawals/{body['withdrawal_id']}/decide",
        json={"action": "mark_paid", "remark": "支付宝已转账 #ZF123"},
        headers=h_a,
    )
    assert decide.status_code == 200
    assert decide.json()["status"] == "paid"


def test_withdrawal_rejection_refunds_balance():
    """C-14：管理员驳回提现 → 已扣除的佣金会被退回。"""
    user = f"wdrawrj_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        u.credits = 100
        u.kyc_status = "approved"
        u.receiving_account_type = "alipay"
        u.receiving_account_name = "Test"
        u.receiving_account_number = "***@a.com"
        db.commit()
    finally:
        db.close()
    sub = client.post("/account/withdrawals", json={"amount": 60}, headers=h).json()
    tk_a = _make_admin_token(f"wdrawrjadm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    rj = client.post(
        f"/admin/withdrawals/{sub['withdrawal_id']}/decide",
        json={"action": "reject", "remark": "账户信息不符"},
        headers=h_a,
    )
    assert rj.status_code == 200
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        assert u.credits == 100  # 已退回
    finally:
        db.close()


def test_withdrawal_deducts_credits_before_commission_balance():
    """提现冻结：优先扣 credits，不足部分扣 commission_balance（payout.split_deduction）。"""
    user = f"wdsplit_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        u.credits = 30
        u.commission_balance = 50
        u.kyc_status = "approved"
        u.receiving_account_type = "alipay"
        u.receiving_account_name = "Split Test"
        u.receiving_account_number = "***@a.com"
        db.commit()
    finally:
        db.close()
    sub = client.post("/account/withdrawals", json={"amount": 60}, headers=h)
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert body["credits_balance"] == 0
    assert body["commission_balance"] == 20
    assert body["withdrawable_balance"] == 20
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == user).first()
        assert u.credits == 0
        assert u.commission_balance == 20
    finally:
        db.close()


def test_full_payout_happy_path_from_task_confirm():
    """端到端：接任务 → 验收发奖 → earnings-summary → 收款/KYC → 提现 → 管理员打款。"""
    pub = f"fp_pub_{_unique()}"
    exe = f"fp_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    reward = 100
    client.post("/account/recharge", json={"amount": reward + 50}, headers=pub_headers)
    tr = client.post(
        "/tasks",
        json={
            "title": "提现端到端任务",
            "reward_points": reward,
            "completion_webhook_url": "https://example.com/cb",
        },
        headers=pub_headers,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]
    ar = client.post("/agents/register", json={"name": "PayoutAgent", "description": ""}, headers=exe_headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "done"},
            headers=exe_headers,
        ).status_code == 200
    assert client.post(f"/tasks/{task_id}/confirm", headers=pub_headers).status_code == 200
    bal = client.get("/account/balance", headers=exe_headers).json()
    earned_net = bal["credits"]
    assert earned_net >= 10  # 满足默认最低提现门槛
    es = client.get(f"/agents/{agent_id}/earnings-summary", headers=exe_headers)
    assert es.status_code == 200, es.text
    es_body = es.json()
    assert es_body["tasks_completed"] == 1
    assert es_body["credits_balance"] == earned_net
    assert es_body.get("payout", {}).get("eligible") is False  # 尚未 KYC/收款账户
    recv = client.patch(
        "/account/receiving-account",
        json={"account_type": "alipay", "account_name": "Executor", "account_number": "138****0000"},
        headers=exe_headers,
    )
    assert recv.status_code == 200, recv.text
    kyc_sub = client.post(
        "/account/kyc/personal",
        json={"legal_name": "Executor User", "id_type": "id_card", "id_number": "110101199001011234"},
        headers=exe_headers,
    )
    assert kyc_sub.status_code == 200, kyc_sub.text
    rec_id = kyc_sub.json()["kyc"]["id"]
    tk_a = _make_admin_token(f"fp_adm_{_unique()}")
    h_a = {"Authorization": f"Bearer {tk_a}"}
    assert client.post(f"/admin/kyc/records/{rec_id}/approve", json={}, headers=h_a).status_code == 200
    elig = client.get("/account/payout-eligibility", headers=exe_headers).json()
    assert elig["eligible"] is True
    assert elig["withdrawable_balance"] == earned_net
    withdraw_amt = min(50, earned_net)
    wd = client.post("/account/withdrawals", json={"amount": withdraw_amt}, headers=exe_headers)
    assert wd.status_code == 200, wd.text
    wd_body = wd.json()
    assert wd_body["status"] == "pending"
    assert wd_body["withdrawable_balance"] == earned_net - withdraw_amt
    decide = client.post(
        f"/admin/withdrawals/{wd_body['withdrawal_id']}/decide",
        json={"action": "mark_paid", "remark": "测试打款"},
        headers=h_a,
    )
    assert decide.status_code == 200
    assert decide.json()["status"] == "paid"
    from app.database.relational_db import SessionLocal, User as UserModel
    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == exe).first()
        assert u.credits == earned_net - withdraw_amt
    finally:
        db.close()


# ========================= D-17 工作区 / 团队 =========================


def test_workspace_create_and_invite_flow():
    """D-17：创建工作区、邀请成员、接受邀请、变更角色、移除成员。"""
    owner = f"wsown_{_unique()}"
    tk_o = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h_o = {"Authorization": f"Bearer {tk_o}"}
    create = client.post(
        "/workspaces",
        json={"name": "ACME Studio", "plan": "free"},
        headers=h_o,
    )
    assert create.status_code == 200, create.text
    ws = create.json()
    assert ws["my_role"] == "owner"
    ws_id = ws["id"]
    # 邀请新成员
    invitee_email = f"invitee_{_unique()}@example.com"
    inv = client.post(
        f"/workspaces/{ws_id}/invite",
        json={"email": invitee_email, "role": "publisher"},
        headers=h_o,
    )
    assert inv.status_code == 200, inv.text
    token = inv.json()["token"]
    # 注册被邀请人 + 接受
    invitee = f"wsinv_{_unique()}"
    tk_i = _register_user(invitee, invitee_email, "pw")["access_token"]
    h_i = {"Authorization": f"Bearer {tk_i}"}
    acc = client.post("/workspaces/accept-invite", json={"token": token}, headers=h_i)
    assert acc.status_code == 200, acc.text
    assert acc.json()["joined"] is True
    # 列成员应有 2 人
    members = client.get(f"/workspaces/{ws_id}/members", headers=h_o).json()["members"]
    assert len(members) == 2
    # 升级角色
    invitee_uid = next(m["user_id"] for m in members if m["role"] != "owner")
    upd = client.post(
        f"/workspaces/{ws_id}/members/{invitee_uid}/role",
        json={"role": "admin"},
        headers=h_o,
    )
    assert upd.status_code == 200
    assert upd.json()["role"] == "admin"
    # 移除
    rem = client.delete(f"/workspaces/{ws_id}/members/{invitee_uid}", headers=h_o)
    assert rem.status_code == 200
    assert rem.json()["removed"] is True


def test_workspace_role_gates_recharge_and_publish():
    """D-17：accounting/auditor 不能发布 RFQ；publisher 不能给工作区充值。"""
    owner = f"wsg_o_{_unique()}"
    tk_o = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h_o = {"Authorization": f"Bearer {tk_o}"}
    ws = client.post("/workspaces", json={"name": "GuardCo"}, headers=h_o).json()
    ws_id = ws["id"]
    # 加入一名 publisher 与一名 accounting
    pub = f"wsg_pub_{_unique()}"
    pub_email = f"{pub}@example.com"
    inv1 = client.post(
        f"/workspaces/{ws_id}/invite",
        json={"email": pub_email, "role": "publisher"},
        headers=h_o,
    ).json()
    tk_p = _register_user(pub, pub_email, "pw")["access_token"]
    client.post("/workspaces/accept-invite", json={"token": inv1["token"]}, headers={"Authorization": f"Bearer {tk_p}"})
    acc = f"wsg_acc_{_unique()}"
    acc_email = f"{acc}@example.com"
    inv2 = client.post(
        f"/workspaces/{ws_id}/invite",
        json={"email": acc_email, "role": "accounting"},
        headers=h_o,
    ).json()
    tk_a = _register_user(acc, acc_email, "pw")["access_token"]
    client.post("/workspaces/accept-invite", json={"token": inv2["token"]}, headers={"Authorization": f"Bearer {tk_a}"})
    # publisher 充值 → 403
    r1 = client.post(
        f"/workspaces/{ws_id}/recharge",
        json={"amount": 100},
        headers={"Authorization": f"Bearer {tk_p}"},
    )
    assert r1.status_code == 403
    # accounting 提交 RFQ → 403
    r2 = client.post(
        f"/workspaces/{ws_id}/rfq/submit",
        json={"items": [{"title": "x", "reward_points": 0}]},
        headers={"Authorization": f"Bearer {tk_a}"},
    )
    assert r2.status_code == 403


# ========================= B-9 企业级 RFQ =========================


def test_workspace_rfq_full_flow():
    """B-9：工作区充值 → 预览 → 提交 RFQ → 余额扣减并写出多个 task。"""
    owner = f"rfq_{_unique()}"
    tk = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    ws_id = client.post("/workspaces", json={"name": "BatchCo"}, headers=h).json()["id"]
    # 充值工作区
    r = client.post(
        f"/workspaces/{ws_id}/recharge",
        json={"amount": 200, "note": "首期预付"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["credits"] == 200
    items = [
        {
            "title": "Spec sheet for product A",
            "reward_points": 30,
            "completion_webhook_url": "https://example.com/cb",
            "category": "research",
            "skills": ["docs"],
        },
        {
            "title": "Spec sheet for product B",
            "reward_points": 30,
            "completion_webhook_url": "https://example.com/cb",
            "category": "research",
        },
        {
            "title": "Internal ticket triage (free)",
            "reward_points": 0,
        },
    ]
    pv = client.post(
        f"/workspaces/{ws_id}/rfq/preview",
        json={"items": items},
        headers=h,
    )
    assert pv.status_code == 200, pv.text
    assert pv.json()["credits_required"] == 60
    assert pv.json()["sufficient"] is True
    sub = client.post(
        f"/workspaces/{ws_id}/rfq/submit",
        json={"items": items},
        headers=h,
    )
    assert sub.status_code == 200, sub.text
    body = sub.json()
    assert len(body["tasks"]) == 3
    assert body["credits_charged"] == 60
    assert body["credits_remaining"] == 140


def test_workspace_rfq_rejects_when_insufficient_credits():
    """B-9：余额不足时 RFQ 整批拒绝（原子，不会半提交）。"""
    owner = f"rfqins_{_unique()}"
    tk = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    ws_id = client.post("/workspaces", json={"name": "PoorCo"}, headers=h).json()["id"]
    r = client.post(
        f"/workspaces/{ws_id}/rfq/submit",
        json={
            "items": [
                {
                    "title": "T1",
                    "reward_points": 50,
                    "completion_webhook_url": "https://e.com/cb",
                }
            ]
        },
        headers=h,
    )
    assert r.status_code == 400
    assert "余额不足" in r.json()["detail"]


# ========================= D-18 订阅与席位 =========================


def test_subscription_plans_catalog_public():
    """D-18：订阅计划目录公开可读，含 free / pro / team / enterprise。"""
    r = client.get("/subscriptions/plans")
    assert r.status_code == 200
    codes = {p["code"] for p in r.json()["plans"]}
    assert {"free", "pro", "team", "enterprise"}.issubset(codes)


def test_subscribe_user_pro_deducts_credits_and_grants_monthly():
    """D-18：用户订阅 Pro 扣减任务点并收到月度赠点。"""
    user = f"sub_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post("/account/recharge", json={"amount": 3000}, headers=h)
    before = client.get("/account/me", headers=h).json()["credits"]
    r = client.post(
        "/account/subscription/subscribe",
        json={"plan_code": "pro"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["tier"] == "pro"
    after = client.get("/account/me", headers=h).json()["credits"]
    # pro = 1900 扣款 + 200 赠点 = 净 -1700
    assert after == before - 1900 + 200
    # 再次查询应该返回当前订阅
    sub = client.get("/account/subscription", headers=h).json()
    assert sub["tier"] == "pro"
    assert sub["active_subscription"]["status"] == "active"


def test_subscribe_user_insufficient_credits_fails_cleanly():
    """D-18：任务点余额不足时返回 400 且不会写入订阅。"""
    user = f"subpoor_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    # 默认 credits=0
    r = client.post(
        "/account/subscription/subscribe",
        json={"plan_code": "pro"},
        headers=h,
    )
    assert r.status_code == 400
    sub = client.get("/account/subscription", headers=h).json()
    assert sub["tier"] == "free"


def test_subscribe_workspace_team_updates_plan_and_seats():
    """D-18：工作区订阅 team 档位后 plan/seats 自动升级。"""
    owner = f"wssub_{_unique()}"
    tk = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    ws_id = client.post("/workspaces", json={"name": "SubCo"}, headers=h).json()["id"]
    client.post(f"/workspaces/{ws_id}/recharge", json={"amount": 20000}, headers=h)
    r = client.post(
        f"/workspaces/{ws_id}/subscribe",
        json={"plan_code": "team"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["workspace"]["plan"] == "team"
    assert body["workspace"]["seats"] == 10
    # 订阅会从工作区余额扣掉 9900 并补 1500 月度
    assert body["workspace"]["credits"] == 20000 - 9900 + 1500


def test_subscription_cancel_reverts_to_free():
    """D-18：取消订阅后 tier 回到 free。"""
    user = f"subcan_{_unique()}"
    tk = _register_user(user, f"{user}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    client.post("/account/recharge", json={"amount": 3000}, headers=h)
    client.post("/account/subscription/subscribe", json={"plan_code": "pro"}, headers=h)
    r = client.post("/account/subscription/cancel", headers=h)
    assert r.status_code == 200
    assert r.json()["cancelled"] is True
    sub = client.get("/account/subscription", headers=h).json()
    assert sub["tier"] == "free"


# ========================= D-19 Skill 付费分成 =========================


def _publish_paid_skill(author_token: str, token_str: str, price: int = 20):
    """工具：当前登录作者发布一个 Skill 并设定定价。"""
    # 先把 skill 写到 published_skills 表（绕过上架流程直接插入即可）
    from app.database.relational_db import SessionLocal, PublishedSkill as PS
    db = SessionLocal()
    try:
        row = db.query(PS).filter(PS.skill_token == token_str).first()
        if row is None:
            row = PS(
                skill_token=token_str,
                name=f"Paid Skill {token_str}",
                description="test",
                version_tag="v1",
            )
            db.add(row)
            db.commit()
    finally:
        db.close()
    h = {"Authorization": f"Bearer {author_token}"}
    r = client.post(
        f"/skills/{token_str}/pricing",
        json={"pricing_model": "per_invoke", "price_per_unit": price, "revenue_share_bp": 7000},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_skill_pricing_set_by_author_and_non_author_forbidden():
    """D-19：作者首次定价后其他人无法修改。"""
    author = f"sauth_{_unique()}"
    other = f"soth_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_o = _register_user(other, f"{other}@example.com", "pw")["access_token"]
    token = f"test-skill-{_unique()}"
    _publish_paid_skill(tk_a, token, price=15)
    r = client.post(
        f"/skills/{token}/pricing",
        json={"pricing_model": "per_invoke", "price_per_unit": 99},
        headers={"Authorization": f"Bearer {tk_o}"},
    )
    assert r.status_code == 403


def test_skill_charge_on_task_confirm_splits_author_and_platform():
    """D-19：发布方引用付费 Skill 发任务，confirm 后自动结算作者分成。"""
    author = f"sauth2_{_unique()}"
    publisher = f"spub_{_unique()}"
    executor = f"sexe_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_p = _register_user(publisher, f"{publisher}@example.com", "pw")["access_token"]
    tk_e = _register_user(executor, f"{executor}@example.com", "pw")["access_token"]
    token = f"paid-skill-{_unique()}"
    _publish_paid_skill(tk_a, token, price=40)
    h_p = {"Authorization": f"Bearer {tk_p}"}
    h_e = {"Authorization": f"Bearer {tk_e}"}
    client.post("/account/recharge", json={"amount": 500}, headers=h_p)
    # 发任务（reward=20，执行者完成后发布方还需额外支付 40 点 Skill 分成）
    pub = client.post(
        "/tasks",
        json={
            "title": "use paid skill",
            "description": "x",
            "task_type": "general",
            "reward_points": 20,
            "completion_webhook_url": "https://example.com/cb",
            "related_skill_token": token,
        },
        headers=h_p,
    )
    assert pub.status_code == 200, pub.text
    task_id = pub.json()["id"]
    # 注册 Agent 接取并完成
    ar = client.post(
        "/agents/register",
        json={"name": f"a_{_unique()}", "agent_type": "research"},
        headers=h_e,
    )
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=h_e)
    client.post(f"/tasks/{task_id}/claim", json={"agent_id": agent_id}, headers=h_e)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        sub_r = client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"agent_id": agent_id, "result_summary": "done"},
            headers=h_e,
        )
    assert sub_r.status_code == 200, sub_r.text
    # 发布方确认
    conf = client.post(f"/tasks/{task_id}/confirm", headers=h_p)
    assert conf.status_code == 200, conf.text
    # 验证作者收到分成（70% 的 40 = 28）
    rev = client.get("/account/skill-revenue", headers={"Authorization": f"Bearer {tk_a}"})
    assert rev.status_code == 200
    body = rev.json()
    assert body["total"] >= 1
    found = [it for it in body["items"] if it["skill_token"] == token]
    assert found
    assert found[0]["gross_amount"] == 40
    assert found[0]["author_payout"] == 28
    assert found[0]["platform_fee"] == 12


def test_skill_charge_idempotent_per_task():
    """D-19：同一 task 重复触发不会重复计费。"""
    author = f"sauth3_{_unique()}"
    buyer = f"sbuy_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_b = _register_user(buyer, f"{buyer}@example.com", "pw")["access_token"]
    token = f"idem-skill-{_unique()}"
    _publish_paid_skill(tk_a, token, price=10)
    h_b = {"Authorization": f"Bearer {tk_b}"}
    client.post("/account/recharge", json={"amount": 200}, headers=h_b)
    # 建一个真实的 task 供 invoke 引用
    t = client.post(
        "/tasks",
        json={"title": "idempotency holder", "reward_points": 0, "task_type": "general"},
        headers=h_b,
    )
    tid = t.json()["id"]
    r1 = client.post(
        f"/skills/{token}/charge",
        params={"event_kind": "download"},
        headers=h_b,
    )
    assert r1.status_code == 200
    assert r1.json()["charged"] is True
    r2 = client.post(
        f"/skills/{token}/charge",
        params={"event_kind": "invoke", "related_task_id": tid},
        headers=h_b,
    )
    assert r2.status_code == 200
    r3 = client.post(
        f"/skills/{token}/charge",
        params={"event_kind": "invoke", "related_task_id": tid},
        headers=h_b,
    )
    assert r3.status_code == 200
    assert r2.json()["share"]["id"] == r3.json()["share"]["id"]


def _publish_paid_skill_with_model(author_token, token_str, pricing_model, price):
    from app.database.relational_db import SessionLocal, PublishedSkill as PS
    db = SessionLocal()
    try:
        row = db.query(PS).filter(PS.skill_token == token_str).first()
        if row is None:
            row = PS(skill_token=token_str, name=f"Paid {token_str}", description="t", version_tag="v1")
            db.add(row)
            db.commit()
    finally:
        db.close()
    h = {"Authorization": f"Bearer {author_token}"}
    r = client.post(
        f"/skills/{token_str}/pricing",
        json={"pricing_model": pricing_model, "price_per_unit": price, "revenue_share_bp": 7000},
        headers=h,
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_skill_purchase_download_idempotent_and_grants_entitlement():
    """D-19：per_download 购买扣点、授予权益，重复购买幂等不重复扣点。"""
    author = f"pauth_{_unique()}"
    buyer = f"pbuy_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_b = _register_user(buyer, f"{buyer}@example.com", "pw")["access_token"]
    token = f"dl-skill-{_unique()}"
    _publish_paid_skill_with_model(tk_a, token, "per_download", 30)
    h_b = {"Authorization": f"Bearer {tk_b}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h_b)

    # 购买前无权益
    ent0 = client.get(f"/skills/{token}/entitlement", headers=h_b)
    assert ent0.status_code == 200 and ent0.json()["owned"] is False

    r1 = client.post(f"/skills/{token}/purchase", headers=h_b)
    assert r1.status_code == 200, r1.text
    assert r1.json()["created"] is True
    assert r1.json()["credits_remaining"] == 70

    # 再次购买：幂等，不再扣点
    r2 = client.post(f"/skills/{token}/purchase", headers=h_b)
    assert r2.status_code == 200
    assert r2.json()["created"] is False
    assert r2.json()["already_owned"] is True
    assert r2.json()["credits_remaining"] == 70

    # 现已拥有权益
    ent1 = client.get(f"/skills/{token}/entitlement", headers=h_b)
    assert ent1.json()["owned"] is True

    # 作者收入可见（70% of 30 = 21）
    rev = client.get("/account/skill-revenue", headers={"Authorization": f"Bearer {tk_a}"})
    found = [it for it in rev.json()["items"] if it["skill_token"] == token]
    assert found and found[0]["author_payout"] == 21 and found[0]["platform_fee"] == 9


def test_skill_purchase_refund_reverses_credits():
    """D-19：退款窗口内退款冲正买家扣点与作者/平台分成。"""
    author = f"rauth_{_unique()}"
    buyer = f"rbuy_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_b = _register_user(buyer, f"{buyer}@example.com", "pw")["access_token"]
    token = f"rf-skill-{_unique()}"
    _publish_paid_skill_with_model(tk_a, token, "per_download", 40)
    h_b = {"Authorization": f"Bearer {tk_b}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h_b)
    pr = client.post(f"/skills/{token}/purchase", headers=h_b)
    assert pr.json()["credits_remaining"] == 60
    pid = pr.json()["purchase"]["id"]
    assert pr.json()["purchase"]["refundable"] is True

    refund = client.post(f"/skills/purchases/{pid}/refund", headers=h_b)
    assert refund.status_code == 200, refund.text
    assert refund.json()["credits_remaining"] == 100
    assert refund.json()["purchase"]["status"] == "refunded"

    # 权益失效
    ent = client.get(f"/skills/{token}/entitlement", headers=h_b)
    assert ent.json()["owned"] is False

    # 二次退款被拒
    refund2 = client.post(f"/skills/purchases/{pid}/refund", headers=h_b)
    assert refund2.status_code == 400


def test_skill_purchase_rejects_per_invoke_model():
    """per_invoke 类型不能走购买路径（应随任务结算）。"""
    author = f"iauth_{_unique()}"
    buyer = f"ibuy_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_b = _register_user(buyer, f"{buyer}@example.com", "pw")["access_token"]
    token = f"iv-skill-{_unique()}"
    _publish_paid_skill_with_model(tk_a, token, "per_invoke", 20)
    h_b = {"Authorization": f"Bearer {tk_b}"}
    client.post("/account/recharge", json={"amount": 100}, headers=h_b)
    r = client.post(f"/skills/{token}/purchase", headers=h_b)
    assert r.status_code == 400


def test_skill_purchase_insufficient_credits_rejected():
    """余额不足时购买被拒，不产生权益。"""
    author = f"nauth_{_unique()}"
    buyer = f"nbuy_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    tk_b = _register_user(buyer, f"{buyer}@example.com", "pw")["access_token"]
    token = f"nf-skill-{_unique()}"
    _publish_paid_skill_with_model(tk_a, token, "per_download", 999)
    h_b = {"Authorization": f"Bearer {tk_b}"}
    r = client.post(f"/skills/{token}/purchase", headers=h_b)
    assert r.status_code == 400
    purchases = client.get("/account/skill-purchases", headers=h_b)
    assert purchases.status_code == 200
    assert all(it["skill_token"] != token for it in purchases.json()["items"])


def test_skill_pricing_appears_in_marketplace_listing():
    """市场列表返回定价字段，供前端展示价格 Badge。"""
    author = f"mauth_{_unique()}"
    tk_a = _register_user(author, f"{author}@example.com", "pw")["access_token"]
    token = f"mk-skill-{_unique()}"
    _publish_paid_skill_with_model(tk_a, token, "per_download", 25)
    lst = client.get("/skills", params={"limit": 200})
    assert lst.status_code == 200
    found = [it for it in lst.json()["items"] if it["skill_token"] == token]
    assert found
    assert found[0]["pricing_model"] == "per_download"
    assert found[0]["price_per_unit"] == 25


def test_workspace_rfq_blocked_by_safety_gate():
    """B-9 + C-13：RFQ 提交也走内容安全网关。"""
    os.environ["SAFETY_BLACKLIST"] = "forbidden_keyword_rfq"
    owner = f"rfqsafe_{_unique()}"
    tk = _register_user(owner, f"{owner}@example.com", "pw")["access_token"]
    h = {"Authorization": f"Bearer {tk}"}
    ws_id = client.post("/workspaces", json={"name": "SafeCo"}, headers=h).json()["id"]
    client.post(f"/workspaces/{ws_id}/recharge", json={"amount": 100}, headers=h)
    r = client.post(
        f"/workspaces/{ws_id}/rfq/submit",
        json={
            "items": [
                {
                    "title": "Normal task",
                    "reward_points": 10,
                    "completion_webhook_url": "https://e.com/cb",
                },
                {
                    "title": "this contains forbidden_keyword_rfq please block",
                    "reward_points": 10,
                    "completion_webhook_url": "https://e.com/cb",
                },
            ]
        },
        headers=h,
    )
    assert r.status_code == 400
    os.environ.pop("SAFETY_BLACKLIST", None)


# ---------------------------------------------------------------------------
# register-via-skill 验证收紧 + 隐藏内部任务
# ---------------------------------------------------------------------------


def test_register_via_skill_rejects_placeholder_template():
    """模板占位词（如 【verify】）直接拒绝，避免测试任务污染公开大厅。"""
    st = _register_via_skill_second_task_json()
    st["title"] = "【verify】deploy smoke test"
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "placeholder-test",
            "description": "test",
            "agent_type": "general",
            "second_task": st,
        },
    )
    assert r.status_code == 400, r.text
    assert "模板" in r.text or "占位" in r.text


def test_register_via_skill_rejects_missing_sections():
    """缺失 SKILL.md 模板必备小节时拒绝。"""
    st = _register_via_skill_second_task_json()
    st["description"] = "A" * 200  # 够长但无任何小节
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "missing-sections",
            "description": "test",
            "agent_type": "general",
            "second_task": st,
        },
    )
    assert r.status_code == 400, r.text
    assert "小节" in r.text


def test_register_via_skill_handshake_task_hidden_from_public():
    """注册产生的握手任务不应出现在公开大厅，但第二条任务会出现。"""
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "HiddenHandshakeAgent",
            "description": "pytest hides handshake",
            "agent_type": "general",
            "second_task": _register_via_skill_second_task_json(),
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    tasks = data.get("auto_published_tasks") or []
    assert len(tasks) == 2
    handshake_id = tasks[0]["id"]
    second_id = tasks[1]["id"]

    # 公开大厅不允许露出握手任务
    lst = client.get("/tasks", params={"limit": 200}).json()
    ids = {t["id"] for t in lst.get("tasks") or []}
    assert handshake_id not in ids, "handshake task must be hidden from public listing"
    # 第二条（真实 Skill 生成）应当出现
    assert second_id in ids


def test_register_via_skill_internal_probe_marks_hidden(monkeypatch):
    """内部探活：携带正确 probe token 时，第二条任务也会被标记 hidden_from_public。"""
    monkeypatch.setenv("CLAWJOB_INTERNAL_PROBE_TOKEN", "probe-secret-xyz")
    st = {
        "title": "[internal] deploy health probe",
        "description": "internal probe description that is reasonably long enough to pass >=40 chars",
        "task_type": "general",
        "priority": "low",
        "reward_points": 0,
        "category": "other",
    }
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": "DeployProbeAgent",
            "description": "probe",
            "agent_type": "general",
            "second_task": st,
            "internal_probe_token": "probe-secret-xyz",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
    tasks = data.get("auto_published_tasks") or []
    assert len(tasks) == 2
    second_id = tasks[1]["id"]
    # 公开大厅不应出现内部探活任务
    lst = client.get("/tasks", params={"limit": 200}).json()
    ids = {t["id"] for t in lst.get("tasks") or []}
    assert second_id not in ids


def test_internal_probe_title_hidden_without_token():
    """标题含 [internal] 探活特征时，即使无 probe token 也不进公开大厅。"""
    st = {
        "title": "[internal] deploy health probe (do not pick up)",
        "description": "internal probe description that is reasonably long enough to pass >=40 chars",
        "task_type": "general",
        "priority": "low",
        "reward_points": 0,
        "category": "other",
    }
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": f"ProbeNoToken_{_unique()}",
            "description": "probe",
            "agent_type": "general",
            "second_task": st,
        },
    )
    assert r.status_code == 200, r.text
    second_id = (r.json().get("auto_published_tasks") or [])[1]["id"]
    lst = client.get("/tasks", params={"limit": 200}).json()
    ids = {t["id"] for t in lst.get("tasks") or []}
    assert second_id not in ids


def test_probe_agents_excluded_from_public_stats_and_candidates():
    """探活命名 Agent 不计入公开统计与候选列表。"""
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"probe_e2e_{_unique()}", "description": "deploy probe"},
    )
    assert r.status_code == 200, r.text
    probe_id = r.json()["agent_id"]

    after = client.get("/stats").json()
    cand = client.get("/candidates", params={"limit": 500}).json()
    cand_ids = {c["id"] for c in (cand.get("candidates") or [])}
    assert probe_id not in cand_ids

    from app.database.relational_db import SessionLocal, Agent, User
    from app.domain.agent_public import agent_is_public

    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == probe_id).first()
        owner = db.query(User).filter(User.id == agent.owner_id).first()
        assert agent is not None
        assert not agent_is_public(agent, owner), "probe agent must be non-public"
    finally:
        db.close()


def test_community_message_supports_multimodal_attachments():
    """社区消息允许 content + 附件（image/file/link 等）。"""
    u = f"cm_user_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass123")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post("/agents/register", json={"name": "cm-agent", "description": "community"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]

    gen = client.post(
        "/community/topics/auto-generate",
        json={"agent_id": agent_id, "skill_tags": ["development"], "force": True},
        headers=headers,
    )
    assert gen.status_code == 200, gen.text
    created = gen.json().get("created") or []
    assert created, "should auto-generate at least one topic"
    topic_id = int(created[0]["id"])

    r = client.post(
        f"/community/topics/{topic_id}/messages",
        json={
            "content": "这是一个带多模态附件的消息",
            "agent_id": agent_id,
            "intent": "question",
            "attachments": [
                {"kind": "image", "url": "https://example.com/demo.png", "name": "demo image"},
                {"kind": "file", "url": "https://example.com/spec.pdf", "name": "spec"},
                {"kind": "link", "url": "https://clawjob.com.cn"},
            ],
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    msg = data["message"]
    assert msg["content_md"] == "这是一个带多模态附件的消息"
    assert msg.get("intent") == "question"
    assert isinstance(msg.get("attachments"), list)
    assert len(msg["attachments"]) == 3
    assert msg["attachments"][0]["kind"] == "image"


def test_community_message_rejects_empty_content_and_attachments():
    """社区消息内容与附件不能同时为空。"""
    u = f"cm_empty_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass123")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post("/agents/register", json={"name": "cm-empty-agent", "description": "community"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    gen = client.post(
        "/community/topics/auto-generate",
        json={"agent_id": agent_id, "skill_tags": ["general"], "force": True},
        headers=headers,
    )
    assert gen.status_code == 200, gen.text
    topic_id = int((gen.json().get("created") or [])[0]["id"])

    r = client.post(
        f"/community/topics/{topic_id}/messages",
        json={"content": "   ", "agent_id": agent_id, "attachments": []},
        headers=headers,
    )
    assert r.status_code == 400, r.text
    assert "同时为空" in r.text


def test_community_reply_supports_video_attachment():
    """社区回复支持 reply_to_id + video/image 附件。"""
    u = f"cm_reply_{_unique()}"
    email = f"{u}@example.com"
    token = _register_user(u, email, "pass123")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post("/agents/register", json={"name": "cm-reply-agent", "description": "community"}, headers=headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]

    gen = client.post(
        "/community/topics/auto-generate",
        json={"agent_id": agent_id, "skill_tags": ["development"], "force": True},
        headers=headers,
    )
    assert gen.status_code == 200, gen.text
    topic_id = int((gen.json().get("created") or [])[0]["id"])

    parent = client.post(
        f"/community/topics/{topic_id}/messages",
        json={"content": "parent message", "agent_id": agent_id},
        headers=headers,
    )
    assert parent.status_code == 200, parent.text
    parent_id = int(parent.json()["message"]["id"])

    reply = client.post(
        f"/community/topics/{topic_id}/messages",
        json={
            "content": "video reply",
            "agent_id": agent_id,
            "reply_to_id": parent_id,
            "attachments": [
                {"kind": "video", "url": "https://example.com/demo.mp4", "mime_type": "video/mp4"},
                {"kind": "image", "url": "https://example.com/frame.png"},
            ],
        },
        headers=headers,
    )
    assert reply.status_code == 200, reply.text
    msg = reply.json()["message"]
    assert msg["reply_to_id"] == parent_id
    assert len(msg.get("attachments") or []) == 2
    assert msg["attachments"][0]["kind"] == "video"


def test_community_filters_ops_daily_from_public_list():
    """运营日报（ClawJob-Ops 模式）不出现在公开话题消息列表。"""
    u = f"cm_ops_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pass123")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    ar = client.post(
        "/agents/register",
        json={"name": "ClawJob-Ops", "description": "ops test agent"},
        headers=headers,
    )
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    gen = client.post(
        "/community/topics/auto-generate",
        json={"agent_id": agent_id, "skill_tags": ["general"], "force": True},
        headers=headers,
    )
    assert gen.status_code == 200, gen.text
    topic_id = int((gen.json().get("created") or [])[0]["id"])

    ops_post = client.post(
        f"/community/topics/{topic_id}/messages",
        json={
            "agent_id": agent_id,
            "content": "📊 ClawJob 每日增长运营日报 · 2026-06-01\n· 公开 Agent 57/200",
            "intent": "recap",
        },
        headers=headers,
    )
    assert ops_post.status_code == 200, ops_post.text

    normal_post = client.post(
        f"/community/topics/{topic_id}/messages",
        json={"agent_id": agent_id, "content": "普通用户讨论帖", "intent": "tip"},
        headers=headers,
    )
    assert normal_post.status_code == 200, normal_post.text

    listed = client.get(f"/community/topics/{topic_id}/messages")
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items") or []
    bodies = [m.get("content_md") or "" for m in items]
    assert any("普通用户讨论帖" in b for b in bodies)
    assert not any("每日增长运营日报" in b for b in bodies)


def test_community_push_skill_to_agent():
    """聊天中可将 Skill 推送给指定 Agent（站内信）。"""
    u1 = f"push_skill_src_{_unique()}"
    t1 = _register_user(u1, f"{u1}@example.com", "pass123")["access_token"]
    h1 = {"Authorization": f"Bearer {t1}"}
    skill_token = f"skill_push_{_unique()}"
    a1 = client.post(
        "/agents/register",
        json={"name": "push-src-agent", "description": "src", "skill_bound_token": skill_token},
        headers=h1,
    )
    assert a1.status_code == 200, a1.text
    src_agent_id = int(a1.json()["id"])

    u2 = f"push_skill_dst_{_unique()}"
    t2 = _register_user(u2, f"{u2}@example.com", "pass123")["access_token"]
    h2 = {"Authorization": f"Bearer {t2}"}
    a2 = client.post("/agents/register", json={"name": "push-dst-agent", "description": "dst"}, headers=h2)
    assert a2.status_code == 200, a2.text
    dst_agent_id = int(a2.json()["id"])

    sp = client.post(
        "/skills/publish",
        json={
            "skill_token": skill_token,
            "name": "Push Skill Demo",
            "description": "for community push test",
            "download_skill_url": "https://example.com/skill.zip",
        },
        headers=h1,
    )
    assert sp.status_code == 200, sp.text
    skill_id = int(sp.json()["id"])

    gen = client.post(
        "/community/topics/auto-generate",
        json={"agent_id": src_agent_id, "skill_tags": ["development"], "force": True},
        headers=h1,
    )
    assert gen.status_code == 200, gen.text
    topic_id = int((gen.json().get("created") or [])[0]["id"])

    ps = client.post(
        f"/community/topics/{topic_id}/push-skill",
        json={
            "from_agent_id": src_agent_id,
            "target_agent_id": dst_agent_id,
            "skill_id": skill_id,
            "note": "请评估并安装这个 skill",
        },
        headers=h1,
    )
    assert ps.status_code == 200, ps.text
    data = ps.json()
    assert data.get("ok") is True
    assert int(data.get("target_agent_id") or -1) == dst_agent_id
    assert int(data.get("skill", {}).get("id") or -1) == skill_id


def test_community_dispatch_hot_legacy_route_removed():
    """旧版 /community/dispatch/hot 任意用户可触发，已移除；应返回 404。"""
    u = f"legacy_dispatch_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pass123")["access_token"]
    r = client.post("/community/dispatch/hot", params={"top_limit": 3}, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_admin_community_dispatch_hot_requires_superuser():
    """热议分发仅限超级管理员。"""
    norm = f"disp_norm_{_unique()}"
    tk_n = _register_user(norm, f"{norm}@example.com", "pw")["access_token"]
    r_forbid = client.post(
        "/admin/community/dispatch-hot",
        params={"top_limit": 3},
        headers={"Authorization": f"Bearer {tk_n}"},
    )
    assert r_forbid.status_code == 403

    adm = f"disp_adm_{_unique()}"
    tk_a = _make_admin_token(adm)
    r_ok = client.post(
        "/admin/community/dispatch-hot",
        params={"top_limit": 3},
        headers={"Authorization": f"Bearer {tk_a}"},
    )
    assert r_ok.status_code == 200, r_ok.text
    body = r_ok.json()
    assert body.get("ok") is True
    assert "topics" in body and "dispatched" in body


def test_skills_packs_public():
    """场景 Skill 包列表对 Agent 公开可读。"""
    r = client.get("/skills/packs")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("total", 0) >= 3
    items = data.get("items") or []
    assert any(i.get("id") == "openclaw-starter" for i in items)
    assert all("install_copy" in i for i in items)
    assert all("why_this_pack_zh" in i for i in items)
    assert all("open_tasks_count" in i for i in items)
    r2 = client.get("/skills/packs", params={"scenario": "writing"})
    assert r2.status_code == 200
    assert all(i.get("scenario") == "writing" for i in (r2.json().get("items") or []))


def test_well_known_clawjob_agent_manifest():
    """公开 Agent 发现清单含注册入口与统计字段。"""
    r = client.get("/.well-known/clawjob-agent.json")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("register", {}).get("minimal", {}).get("url")
    assert "tasks_open" in (data.get("stats") or {})
    assert "agents_count" in (data.get("stats") or {})
    assert isinstance(data.get("skill_packs"), list)
    assert "onboarding_quest" in data
    assert "sample_open_tasks" in data
    assert "referral" in data
    assert "trust_card_sample_url" in data
    assert "platform_moats_zh" in data
    eps = data.get("endpoints") or {}
    assert "trust_card_pattern" in eps


def test_agent_opportunities_feed():
    """公开 Agent 发现 feed：开放任务数、Top 奖励、注册 curl、onboarding ids。"""
    r = client.get("/public/agent-opportunities.json")
    assert r.status_code == 200, r.text
    data = r.json()
    assert "open_tasks_count" in data
    assert isinstance(data.get("top_tasks_by_reward"), list)
    assert data.get("register", {}).get("curl")
    assert isinstance(data.get("onboarding_quest_ids"), list)
    assert data.get("platform_moats_one_liner_zh")
    assert data.get("referral", {}).get("join_with_ref_pattern")
    assert "withdrawal_min" in data
    assert isinstance(data.get("payout_steps_zh"), list)
    assert "money_loop_zh" in data
    assert "agent_direct" in (data.get("money_loop_zh") or "")


def test_public_open_task_counts_exclude_internal_probe():
    """内部探活任务不进公开 feed/sample，且不计入公开 open 计数。"""
    st = {
        "title": "[internal] deploy health probe (do not pick up)",
        "description": "internal probe description that is reasonably long enough to pass >=40 chars",
        "task_type": "general",
        "priority": "low",
        "reward_points": 0,
        "category": "other",
    }
    r = client.post(
        "/auth/register-via-skill",
        json={
            "agent_name": f"CountAlign_{_unique()}",
            "description": "count align test",
            "agent_type": "general",
            "second_task": st,
        },
    )
    assert r.status_code == 200, r.text
    probe_id = (r.json().get("auto_published_tasks") or [])[1]["id"]

    from app.database.relational_db import SessionLocal, Task, User
    from app.domain.task_helpers import task_is_public_listing

    db = SessionLocal()
    try:
        t = db.query(Task).filter(Task.id == probe_id).first()
        owner = db.query(User).filter(User.id == t.owner_id).first()
        assert t is not None
        assert not task_is_public_listing(t, owner), "internal probe must not be public listing"
    finally:
        db.close()

    stats = client.get("/stats").json()
    manifest = client.get("/.well-known/clawjob-agent.json").json()
    feed = client.get("/public/agent-opportunities.json").json()

    assert int(manifest["stats"]["tasks_open"]) == int(stats["tasks_open"])
    assert int(feed["open_tasks_count"]) == int(stats["tasks_open"])

    top_ids = {t["id"] for t in (feed.get("top_tasks_by_reward") or [])}
    sample_ids = {t["id"] for t in (feed.get("sample_open_tasks") or [])}
    assert probe_id not in top_ids
    assert probe_id not in sample_ids
    assert probe_id not in {t["id"] for t in (manifest.get("sample_open_tasks") or [])}
    assert "agent_direct" in (feed.get("money_loop_zh") or "")

    lst = client.get("/tasks", params={"limit": 200}).json()
    public_ids = {t["id"] for t in lst.get("tasks") or []}
    assert probe_id not in public_ids


def test_referral_program_public():
    r = client.get("/public/referral-program.json")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("referral_landing_pattern")
    assert "/#/r/" in data["referral_landing_pattern"]
    assert data.get("referrer_bonus_points") is not None
    assert data.get("money_narrative_zh")
    assert "agent_direct" in (data.get("money_narrative_zh") or "")


def test_account_referral_link_format():
    ref = f"reflink_{_unique()}"
    tk = _register_user(ref, f"{ref}@example.com", "pw")["access_token"]
    my = client.get("/account/referral", headers={"Authorization": f"Bearer {tk}"}).json()
    assert my.get("referral_code")
    assert "/#/r/" in (my.get("referral_link") or "")
    assert my.get("invited_count") == 0


def test_well_known_links_agent_opportunities():
    r = client.get("/.well-known/clawjob-agent.json")
    assert r.status_code == 200
    eps = r.json().get("endpoints") or {}
    assert "agent_opportunities" in eps
    assert "/public/agent-opportunities.json" in eps["agent_opportunities"]
    assert "referral_program" in eps
    assert "payout_eligibility" in eps
    assert "earnings_summary_pattern" in eps


def test_register_minimal_first_subscribe_nudge_inbox():
    """零订阅 Agent 注册后收到最高奖励任务站内信。"""
    from app.database.relational_db import SessionLocal, InternalMessage, Task

    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"Nudge_{_unique()}", "description": "nudge test"},
    )
    assert r.status_code == 200, r.text
    user_id = r.json()["user_id"]
    db = SessionLocal()
    try:
        msgs = (
            db.query(InternalMessage)
            .filter(InternalMessage.recipient_user_id == user_id)
            .order_by(InternalMessage.id.desc())
            .all()
        )
        titles = [m.title for m in msgs]
        assert "接取你的第一个任务" in titles
        nudge = next(m for m in msgs if m.title == "接取你的第一个任务")
        assert nudge.related_task_id is not None
        task = db.query(Task).filter(Task.id == nudge.related_task_id).first()
        assert task is not None
        assert task.status == "open"
    finally:
        db.close()


def test_task_list_includes_category_completions():
    r = client.get("/tasks", params={"limit": 5})
    assert r.status_code == 200, r.text
    tasks = r.json().get("tasks") or []
    if tasks:
        assert "category_completions" in tasks[0]


def test_well_known_onboarding_quest_count_after_seed():
    """well-known manifest onboarding_quest.count 在 seed 后应 >= 3。"""
    from app.database.relational_db import SessionLocal
    from app.services.onboarding_quest import seed_onboarding_quest_tasks

    db = SessionLocal()
    try:
        seed_onboarding_quest_tasks(db, apply=True)
    finally:
        db.close()

    manifest = client.get("/.well-known/clawjob-agent.json").json()
    oq = manifest.get("onboarding_quest") or {}
    assert int(oq.get("count") or 0) >= 3, manifest.get("onboarding_quest")
    assert len(manifest.get("onboarding_quest_ids") or []) >= 3

    feed = client.get("/public/agent-opportunities.json").json()
    assert len(feed.get("onboarding_quest_ids") or []) >= 3


def test_seed_onboarding_quest_idempotent():
    from app.database.relational_db import SessionLocal
    from app.services.onboarding_quest import seed_onboarding_quest_tasks

    db = SessionLocal()
    try:
        n1 = seed_onboarding_quest_tasks(db, apply=True)
        n2 = seed_onboarding_quest_tasks(db, apply=True)
        assert n1 >= 3 or n2 == 0
        assert n2 == 0
    finally:
        db.close()


def test_register_minimal_includes_onboarding_quest():
    from app.database.relational_db import SessionLocal
    from app.services.onboarding_quest import seed_onboarding_quest_tasks

    db = SessionLocal()
    try:
        seed_onboarding_quest_tasks(db, apply=True)
    finally:
        db.close()
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"Quest_{_unique()}", "description": "onboarding quest test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    ids = data.get("onboarding_task_ids") or []
    assert len(ids) >= 3
    assert len(data.get("onboarding_tasks") or []) >= 3
    assert data.get("next_steps", {}).get("onboarding_task_ids")


def test_cleanup_ops_preserves_onboarding_quests():
    """cleanup_ops_content must not delete seed_onboarding_quest / 【新手 Quest tasks."""
    from app.database.relational_db import Agent, SessionLocal, Task, User
    from app.services.onboarding_quest import seed_onboarding_quest_tasks
    from scripts.cleanup_ops_content import _task_delete_reason

    db = SessionLocal()
    try:
        seed_onboarding_quest_tasks(db, apply=True)
        tasks = (
            db.query(Task)
            .filter(Task.title.like("【新手 Quest%"))
            .all()
        )
        assert len(tasks) >= 3
        for task in tasks:
            owner = db.query(User).filter(User.id == task.owner_id).first()
            creator = (
                db.query(Agent).filter(Agent.id == task.creator_agent_id).first()
                if task.creator_agent_id
                else None
            )
            reason = _task_delete_reason(task, owner, creator, ops_agent_ids=set(), ops_owner_ids=set())
            assert reason is None, f"onboarding task {task.id} would be deleted: {reason}"
            # Even if mistaken for system owner, onboarding guard must win
            reason2 = _task_delete_reason(
                task, owner, creator, ops_agent_ids={int(creator.id)} if creator else set(), ops_owner_ids={int(owner.id)} if owner else set()
            )
            assert reason2 is None, f"onboarding task {task.id} deleted under ops ids: {reason2}"
            extra = task.input_data if isinstance(task.input_data, dict) else {}
            assert extra.get("onboarding") is True or extra.get("source") == "seed_onboarding_quest"
    finally:
        db.close()


def test_register_minimal_referral_message(monkeypatch):
    monkeypatch.setenv("REFERRAL_BONUS_REFERRER", "100")
    monkeypatch.setenv("REFERRAL_BONUS_INVITEE", "50")
    ref = f"refmsg_{_unique()}"
    tk_ref = _register_user(ref, f"{ref}@example.com", "pw")["access_token"]
    my = client.get("/account/referral", headers={"Authorization": f"Bearer {tk_ref}"}).json()
    code = my.get("referral_code") or my.get("code")
    if not code:
        pytest.skip("referral_code not available in test env")
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"RefMsg_{_unique()}", "referral_code": code},
    )
    assert r.status_code == 200, r.text
    assert r.json().get("referral_bound") is True
    assert r.json().get("message")
    assert "50" in r.json().get("message", "")


def test_agent_earnings_summary_owner_only():
    """注册后拥有者可读收益摘要。"""
    r = client.post(
        "/auth/register-agent-minimal",
        json={"agent_name": f"Earn_{_unique()}", "description": "earnings test"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    agent_id = data["agent_id"]
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    es = client.get(f"/agents/{agent_id}/earnings-summary", headers=headers)
    assert es.status_code == 200, es.text
    body = es.json()
    assert body.get("agent_id") == agent_id
    assert body.get("credits_balance") == 500
    assert "reward_points_earned" in body
    assert body.get("links", {}).get("skill_packs")
    other = client.get(f"/agents/{agent_id}/earnings-summary")
    assert other.status_code in (401, 403)


def test_register_agent_minimal_next_steps_has_growth_urls():
    r = client.post("/auth/register-agent-minimal", json={"agent_name": f"Next_{_unique()}"})
    assert r.status_code == 200
    ns = r.json().get("next_steps") or {}
    assert ns.get("earnings_summary_url")
    assert ns.get("skill_packs_url")
    assert ns.get("agent_manifest_url")


def test_sync_skills_from_github_hot(monkeypatch):
    """可从 GitHub 热门仓库同步 Skill 到市场。"""
    async def _fake_fetch(top_n, min_stars, query):
        _ = (top_n, min_stars, query)
        return [
            {
                "full_name": "foo/bar-skill",
                "name": "bar-skill",
                "owner": "foo",
                "html_url": "https://github.com/foo/bar-skill",
                "archive_url": "https://github.com/foo/bar-skill/archive/refs/heads/main.zip",
                "stars": 1234,
                "description": "Great skill repo",
                "topics": ["skill", "agent"],
            }
        ]

    monkeypatch.setattr(app_main, "_fetch_github_hot_skill_repos", _fake_fetch)
    u = f"sync_skill_{_unique()}"
    token = _register_user(u, f"{u}@example.com", "pass123")["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    r = client.post(
        "/skills/sync/github-hot",
        json={"top_n": 5, "min_stars": 50, "force_update": True},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data.get("ok") is True
    assert int(data.get("total") or 0) >= 1
    first = (data.get("items") or [])[0]
    assert "github.com/foo/bar-skill" in (first.get("github_url") or "")


def test_agent_direct_settlement_flow():
    """agent_direct：验收 → settlement pending → 发布方 mark paid → 执行方 confirm；不发平台 credits。"""
    pub = f"ads_pub_{_unique()}"
    exe = f"ads_exe_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    reward = 80
    client.post("/account/recharge", json={"amount": reward + 20}, headers=pub_headers)
    ar = client.post("/agents/register", json={"name": "ExecAgent", "description": ""}, headers=exe_headers)
    assert ar.status_code == 200, ar.text
    agent_id = ar.json()["id"]
    client.put(
        f"/agents/{agent_id}/payment-profile",
        json={
            "methods": [{
                "type": "alipay",
                "label": "支付宝",
                "account_masked": "138****9999",
                "details_for_counterparty": "alipay:13800138000",
            }]
        },
        headers=exe_headers,
    )
    tr = client.post(
        "/tasks",
        json={
            "title": "Agent 直接结算任务",
            "reward_points": reward,
            "completion_webhook_url": "https://example.com/cb",
            "settlement_mode": "agent_direct",
        },
        headers=pub_headers,
    )
    assert tr.status_code == 200, tr.text
    task_id = tr.json()["id"]
    assert client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers).status_code == 200
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        assert client.post(
            f"/tasks/{task_id}/submit-completion",
            json={"result_summary": "done"},
            headers=exe_headers,
        ).status_code == 200
    bal_before = client.get("/account/balance", headers=exe_headers).json()["credits"]
    cr = client.post(f"/tasks/{task_id}/confirm", headers=pub_headers)
    assert cr.status_code == 200, cr.text
    cr_body = cr.json()
    assert cr_body.get("settlement_mode") == "agent_direct"
    assert cr_body.get("settlement", {}).get("status") == "pending"
    assert cr_body.get("reward_paid") == 0
    bal_after = client.get("/account/balance", headers=exe_headers).json()["credits"]
    assert bal_after == bal_before
    pc_fail = client.post(f"/tasks/{task_id}/settlement/payee-confirm", headers=exe_headers)
    assert pc_fail.status_code == 400
    st = client.get(f"/tasks/{task_id}/settlement", headers=pub_headers)
    assert st.status_code == 200, st.text
    st_body = st.json()
    assert st_body["viewer_role"] == "publisher"
    assert st_body["payee_profile"]["methods"][0]["account_masked"] == "138****9999"
    assert st_body["payee_profile"]["methods"][0].get("details_for_counterparty") == "alipay:13800138000"
    mp = client.post(
        f"/tasks/{task_id}/settlement/payer-mark-paid",
        json={"proof_links": ["https://example.com/proof.png"], "note": "已转账"},
        headers=pub_headers,
    )
    assert mp.status_code == 200, mp.text
    assert mp.json()["settlement"].get("payer_confirmed_at")
    pc = client.post(f"/tasks/{task_id}/settlement/payee-confirm", headers=exe_headers)
    assert pc.status_code == 200, pc.text
    assert pc.json()["settlement"]["status"] == "paid"
    assert pc.json()["settlement"].get("payee_confirmed_at")


def test_admin_pending_settlements_and_stats_fields():
    """Admin 结算队列与 /stats settlement 计数字段。"""
    pub = f"adm_set_pub_{_unique()}"
    exe = f"adm_set_exe_{_unique()}"
    admin = f"adm_set_admin_{_unique()}"
    _register_user(pub, f"{pub}@example.com", "pub")
    _register_user(exe, f"{exe}@example.com", "exe")
    _register_user(admin, f"{admin}@example.com", "adminpw")
    pub_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': pub, 'password': 'pub'}).json()['access_token']}"}
    exe_headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': exe, 'password': 'exe'}).json()['access_token']}"}
    admin_token = client.post("/auth/login", json={"username": admin, "password": "adminpw"}).json()["access_token"]
    from app.database.relational_db import SessionLocal, User as UserModel

    db = SessionLocal()
    try:
        u = db.query(UserModel).filter(UserModel.username == admin).first()
        assert u is not None
        u.is_superuser = True
        db.commit()
    finally:
        db.close()
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    reward = 55
    client.post("/account/recharge", json={"amount": reward + 10}, headers=pub_headers)
    ar = client.post("/agents/register", json={"name": "QueueAgent", "description": ""}, headers=exe_headers)
    agent_id = ar.json()["id"]
    client.put(
        f"/agents/{agent_id}/payment-profile",
        json={"methods": [{"type": "alipay", "label": "支付宝", "account_masked": "138****0000", "details_for_counterparty": "alipay:test"}]},
        headers=exe_headers,
    )
    tr = client.post(
        "/tasks",
        json={"title": "Admin queue task", "reward_points": reward, "completion_webhook_url": "https://example.com/cb", "settlement_mode": "agent_direct"},
        headers=pub_headers,
    )
    task_id = tr.json()["id"]
    client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": agent_id}, headers=exe_headers)
    with patch("app.main.httpx") as m:
        m.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        client.post(f"/tasks/{task_id}/submit-completion", json={"result_summary": "done"}, headers=exe_headers)
    client.post(f"/tasks/{task_id}/confirm", headers=pub_headers)

    stats = client.get("/stats")
    assert stats.status_code == 200
    body = stats.json()
    assert "settlement_pending_count" in body
    assert int(body["settlement_pending_count"]) >= 1

    metrics = client.get("/admin/metrics", headers=admin_headers)
    assert metrics.status_code == 200
    mbody = metrics.json()
    assert int(mbody.get("pending_settlements", {}).get("pending_total", 0)) >= 1
    assert "public" in mbody.get("agents", {})

    pending = client.get("/admin/settlements/pending", headers=admin_headers)
    assert pending.status_code == 200
    items = pending.json().get("items") or []
    assert any(it.get("task_id") == task_id for it in items)
    row = next(it for it in items if it.get("task_id") == task_id)
    assert row.get("phase") == "awaiting_payer"

    client.post(
        f"/tasks/{task_id}/settlement/payer-mark-paid",
        json={"proof_links": ["https://example.com/p.png"]},
        headers=pub_headers,
    )
    pending2 = client.get("/admin/settlements/pending", headers=admin_headers)
    row2 = next(it for it in (pending2.json().get("items") or []) if it.get("task_id") == task_id)
    assert row2.get("phase") == "awaiting_payee"

    client.post(f"/tasks/{task_id}/settlement/payee-confirm", headers=exe_headers)
    pending3 = client.get("/admin/settlements/pending", headers=admin_headers)
    assert not any(it.get("task_id") == task_id for it in (pending3.json().get("items") or []))


def test_send_unpicked_reminders_dry_run():
    """24h 无人接取提醒：dry_run 模式只返回任务列表，不写数据库。"""
    u = f"reminder_dry_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw123")
    headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': u, 'password': 'pw123'}).json()['access_token']}"}

    # 发布一个任务（无奖励点，不需要 webhook）
    tr = client.post("/tasks", json={"title": "Dry run reminder task", "reward_points": 0}, headers=headers)
    task_id = tr.json()["id"]

    # 手动把任务的 created_at 往前推 25h
    from app.database.relational_db import SessionLocal, Task as TaskModel
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        assert t is not None
        t.created_at = datetime.utcnow() - timedelta(hours=25)
        db.commit()
    finally:
        db.close()

    r = client.post("/tasks/send-unpicked-reminders?dry_run=true", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["dry_run"] is True
    assert task_id in data["reminded_task_ids"]
    # dry_run 不应写站内信
    inbox_r = client.get("/inbox", headers=headers)
    msgs = inbox_r.json().get("messages") or []
    assert not any(m.get("related_task_id") == task_id and "24h" in m.get("title", "") for m in msgs)


def test_send_unpicked_reminders_actual():
    """24h 无人接取提醒：实际发送后，站内信可见，且同任务不重复发送。"""
    u = f"reminder_act_{_unique()}"
    _register_user(u, f"{u}@example.com", "pw123")
    headers = {"Authorization": f"Bearer {client.post('/auth/login', json={'username': u, 'password': 'pw123'}).json()['access_token']}"}

    tr = client.post("/tasks", json={"title": "Actual reminder task", "reward_points": 0}, headers=headers)
    task_id = tr.json()["id"]

    from app.database.relational_db import SessionLocal, Task as TaskModel
    from datetime import datetime, timedelta
    db = SessionLocal()
    try:
        t = db.query(TaskModel).filter(TaskModel.id == task_id).first()
        t.created_at = datetime.utcnow() - timedelta(hours=26)
        db.commit()
    finally:
        db.close()

    # First call — should remind
    r1 = client.post("/tasks/send-unpicked-reminders", headers=headers)
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert task_id in d1["reminded_task_ids"]

    # Second call — should skip (already reminded)
    r2 = client.post("/tasks/send-unpicked-reminders", headers=headers)
    d2 = r2.json()
    assert task_id not in d2["reminded_task_ids"]
    assert d2["skipped_already_reminded"] > 0


def test_mcp_tools_publish_list_and_marketplace():
    """MCP 工具：POST /tools 持久化后 GET /tools 与 /mcp-tools 可见。"""
    suffix = _unique()
    user = _register_user(f"mcpu{suffix}", f"mcp{suffix}@example.com", "pass12345")
    headers = {"Authorization": f"Bearer {user['access_token']}"}
    tool_name = f"custom_tool_{suffix}"

    r0 = client.get("/tools")
    assert r0.status_code == 200
    before = r0.json()
    before_items = before if isinstance(before, list) else before.get("items", [])

    r = client.post(
        "/tools",
        json={
            "name": tool_name,
            "description": "Test MCP tool",
            "category": "general",
            "return_type": "object",
            "parameters": {"query": {"type": "string"}},
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("status") == "published"
    assert body.get("name") == tool_name
    tool_id = body.get("id")
    assert tool_id is not None

    r2 = client.get("/tools")
    assert r2.status_code == 200
    after = r2.json()
    after_items = after if isinstance(after, list) else after.get("items", [])
    assert len(after_items) >= len(before_items) + 1
    names = {x.get("name") for x in after_items if isinstance(x, dict)}
    assert tool_name in names

    r3 = client.get("/mcp-tools")
    assert r3.status_code == 200
    market = r3.json()
    assert market.get("total", 0) >= 1
    assert any(it.get("name") == tool_name for it in market.get("items", []))

    r4 = client.delete(f"/mcp-tools/{tool_id}", headers=headers)
    assert r4.status_code == 200, r4.text
    assert r4.json().get("ok") is True
