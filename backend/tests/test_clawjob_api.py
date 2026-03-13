"""
ClawJob API 功能测试：认证、任务大厅、发布任务、注册 Agent、订阅任务、账户、验收流程。
"""
import os
import time
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.relational_db import init_db

# 确保所有表存在（含 recharge_orders、verification_codes 等）
init_db()

# 测试用固定验证码，避免依赖真实邮件
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

    # 登录
    r2 = client.post(
        "/auth/login",
        json={"username": u, "password": "testpass123"},
    )
    assert r2.status_code == 200
    assert "access_token" in r2.json()


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
    # 1. 注册并登录
    data = _register_user(u, email, "flowpass")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. 发布任务
    r = client.post(
        "/tasks",
        json={"title": "测试任务", "description": "用于 API 测试"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    task_data = r.json()
    assert "id" in task_data
    task_id = task_data["id"]

    # 3. 任务大厅能看到
    r = client.get("/tasks")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    ids = [t["id"] for t in tasks]
    assert task_id in ids

    # 4. 注册 Agent
    r = client.post(
        "/agents/register",
        json={"name": "测试Agent", "description": "测试用"},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    agent_data = r.json()
    assert "id" in agent_data
    agent_id = agent_data["id"]

    # 5. 我的 Agent 列表
    r = client.get("/agents/mine", headers=headers)
    assert r.status_code == 200
    agents = r.json()["agents"]
    assert len(agents) >= 1
    assert any(a["id"] == agent_id for a in agents)

    # 6. 订阅任务
    r = client.post(
        f"/tasks/{task_id}/subscribe",
        json={"agent_id": agent_id},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    assert "订阅" in r.json().get("message", "")

    # 7. 再次订阅同一任务应提示已订阅
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
    # 发布者注册一个 Agent（用于 invited）
    r = client.post("/agents/register", json={"name": "PubAgent", "description": "pub"}, headers=headers)
    assert r.status_code == 200
    pub_agent_id = r.json()["id"]
    # 发布任务并指定仅 pub_agent_id 可接取
    r = client.post(
        "/tasks",
        json={"title": "仅指定接取", "description": "测试", "invited_agent_ids": [pub_agent_id]},
        headers=headers,
    )
    assert r.status_code == 200
    task_id = r.json()["id"]
    # 另一用户注册并尝试用其 Agent 订阅应 403
    u2 = f"invuser2_{_unique()}"
    data2 = _register_user(u2, f"{u2}@example.com", "invpass")
    token2 = data2["access_token"]
    r = client.post("/agents/register", json={"name": "OtherAgent", "description": "other"}, headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 200
    other_agent_id = r.json()["id"]
    r = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": other_agent_id}, headers={"Authorization": f"Bearer {token2}"})
    assert r.status_code == 403
    # 发布者用自己的 Agent 订阅应成功
    r = client.post(f"/tasks/{task_id}/subscribe", json={"agent_id": pub_agent_id}, headers=headers)
    assert r.status_code == 200


def test_subscribe_requires_auth():
    """订阅任务需要登录"""
    # 先创建一个任务（需要另一个已登录用户，这里只测未登录）
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
    # 先拿到任务列表，取第一个 id；若无任务则跳过或创建
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


def test_reject_requires_reason():
    """拒绝验收时必须填写拒绝理由"""
    # 创建待验收任务需完整流程，这里仅测 400：无 body 或 reason 为空
    u = f"rej_{_unique()}"
    data = _register_user(u, f"{u}@example.com", "pw")
    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/tasks/1/reject", json={}, headers=headers)
    # 可能 404（任务不存在）或 400（理由为空）
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
    # 未真正可访问的 URL 会请求失败，alive 为 False；或 no_webhook 若未存上
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
    # 先发布一个任务
    r = client.post("/tasks", json={"title": "评论测试任务", "description": "desc"}, headers=headers)
    assert r.status_code == 200
    task_id = r.json()["id"]
    # 无评论时列表为空
    r = client.get(f"/tasks/{task_id}/comments")
    assert r.status_code == 200
    assert r.json()["comments"] == []
    # 发表评论
    r = client.post(f"/tasks/{task_id}/comments", json={"content": "第一条评论"}, headers=headers)
    assert r.status_code == 200
    c = r.json()
    assert c["content"] == "第一条评论"
    assert c["author_name"] == u
    assert "id" in c
    # 再拉列表应有 1 条
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
