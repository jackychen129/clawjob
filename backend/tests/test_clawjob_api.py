"""
ClawJob API 功能测试：认证、任务大厅、发布任务、注册 Agent、订阅任务、账户、验收流程。
"""
import time
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.relational_db import init_db

# 确保所有表存在（含 recharge_orders 等新增表）
init_db()

client = TestClient(app)

def _unique():
    return str(int(time.time() * 1000))


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
    assert isinstance(data["tasks"], list)


def test_register_and_login():
    """注册与登录"""
    u = f"testuser_{_unique()}"
    # 注册
    r = client.post(
        "/auth/register",
        json={
            "username": u,
            "email": f"{u}@example.com",
            "password": "testpass123",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()
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
    client.post(
        "/auth/register",
        json={
            "username": "dupuser",
            "email": "dup1@example.com",
            "password": "pass",
        },
    )
    r = client.post(
        "/auth/register",
        json={
            "username": "dupuser",
            "email": "dup2@example.com",
            "password": "pass",
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
    # 1. 注册并登录
    r = client.post(
        "/auth/register",
        json={
            "username": u,
            "email": f"{u}@example.com",
            "password": "flowpass",
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
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
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
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
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    r = client.post("/account/recharge", json={"amount": 100}, headers=headers)
    assert r.status_code == 200
    assert r.json()["credits"] == 100


def test_recharge_order_credit_card():
    """充值订单：信用卡渠道创建订单并确认到账"""
    u = f"ordcard_{_unique()}"
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
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
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
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
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
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
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    token = r.json()["access_token"]
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
    for uname, p in [(pub, "pub"), (exe, "exe")]:
        r = client.post(
            "/auth/register",
            json={"username": uname, "email": f"{uname}@example.com", "password": p},
        )
        assert r.status_code == 200
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


def test_confirm_requires_publisher():
    """仅发布者可验收"""
    u = f"other_{_unique()}"
    r = client.post(
        "/auth/register",
        json={"username": u, "email": f"{u}@example.com", "password": "pw"},
    )
    assert r.status_code == 200
    headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
    r = client.get("/tasks?limit=1")
    assert r.status_code == 200
    tasks = r.json()["tasks"]
    if not tasks:
        pytest.skip("no tasks")
    task_id = tasks[0]["id"]
    r = client.post(f"/tasks/{task_id}/confirm", headers=headers)
    assert r.status_code in (400, 403)
