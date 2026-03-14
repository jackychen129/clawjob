#!/usr/bin/env python3
"""
ClawJob 演示数据种子脚本：创建模拟用户、Agent 与任务，使任务大厅与候选者列表有内容可展示。
使用方式（在 backend 目录或项目根目录执行）：
  python -m scripts.seed_demo_data
  # 或
  PYTHONPATH=. python scripts/seed_demo_data.py
"""
import os
import sys

# 确保 backend 在 PYTHONPATH（从 repo 根或 backend 目录执行均可）
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.database.relational_db import (
    SessionLocal,
    init_db,
    User,
    Agent,
    Task,
)
from app.security import get_password_hash


DEMO_PASSWORD = "demo123"

USERS = [
    {"username": "alice", "email": "alice@example.com"},
    {"username": "bob", "email": "bob@example.com"},
    {"username": "carol", "email": "carol@example.com"},
]

AGENTS = [
    {"name": "DataRunner", "owner_username": "alice", "agent_type": "数据分析", "description": "数据分析与报表生成，支持 CSV / SQL 与可视化。"},
    {"name": "DocGen", "owner_username": "bob", "agent_type": "文档", "description": "技术文档与 README 自动生成，多语言与 Markdown 支持。"},
    {"name": "CodeReview Bot", "owner_username": "carol", "agent_type": "开发", "description": "代码审查与基础安全扫描，适用于 PR 与日常提交。"},
    {"name": "Research Assistant", "owner_username": "alice", "agent_type": "调研", "description": "文献检索与摘要，协助调研与竞品分析。"},
    {"name": "Translate Pro", "owner_username": "bob", "agent_type": "翻译", "description": "中英日多语言翻译与术语统一，适合技术文档。"},
    {"name": "AutoTester", "owner_username": "carol", "agent_type": "测试", "description": "自动化测试脚本生成与执行，集成常见测试框架。"},
    {"name": "Nova", "owner_username": "bob", "agent_type": "开发", "description": "全栈开发与 API 集成，支持 Python、TypeScript 与常见框架。"},
    {"name": "Aria", "owner_username": "alice", "agent_type": "文案", "description": "营销文案与落地页撰写，SEO 与转化导向。"},
    {"name": "Atlas", "owner_username": "carol", "agent_type": "调研", "description": "市场与行业调研，输出结构化报告与数据摘要。"},
    {"name": "Sage", "owner_username": "alice", "agent_type": "文档", "description": "API 文档与用户手册生成，支持 OpenAPI 与 Markdown。"},
]

# 参考众包/Agent 平台与常见远程任务：数据、文档、开发、调研、翻译、测试等
TASKS = [
    {"title": "图像分类标注（500 张）", "description": "对提供的 500 张产品图按给定类别进行标注，输出 CSV；需保证类别一致、无漏标。", "task_type": "数据分析", "reward_points": 45, "location": "远程", "duration_estimate": "~2h", "skills": ["数据标注", "图像分类"]},
    {"title": "客服工单摘要（10 条）", "description": "将 10 条客服对话整理为结构化摘要：问题类型、结论、建议操作；输出 Markdown 表格。", "task_type": "文档", "reward_points": 35, "location": "远程", "duration_estimate": "~1h", "skills": ["文档", "摘要"]},
    {"title": "登录模块单元测试", "description": "为现有登录 API 编写单元测试，覆盖正常登录、错误密码、过期 token 等至少 5 个用例。", "task_type": "开发", "reward_points": 80, "location": "远程", "duration_estimate": "~2h", "skills": ["测试", "API"]},
    {"title": "竞品功能与定价对比（3 款）", "description": "选取 3 款同类 SaaS 产品，整理核心功能与定价方案，输出对比表与简要结论。", "task_type": "调研", "reward_points": 95, "location": "远程", "duration_estimate": "~3h", "skills": ["调研", "竞品分析"]},
    {"title": "产品页文案中译英", "description": "将一段中文产品介绍（约 800 字）翻译为英文，保持语气与卖点一致，适合海外落地页。", "task_type": "翻译", "reward_points": 55, "location": "远程", "duration_estimate": "~1.5h", "skills": ["翻译", "文案"]},
    {"title": "API 集成测试脚本", "description": "为指定 REST API 编写 5 个端到端测试用例（pytest + requests），附 README 说明运行方式。", "task_type": "测试", "reward_points": 70, "location": "远程", "duration_estimate": "~2.5h", "skills": ["Python", "pytest", "API"]},
    {"title": "周报数据汇总与图表", "description": "将本周各渠道的 CSV 数据汇总，生成一份带图表的 Markdown 周报。", "task_type": "数据分析", "reward_points": 50, "location": "远程", "duration_estimate": "~2h", "skills": ["数据分析", "Markdown", "图表"]},
    {"title": "技术博客草稿（1500 字）", "description": "根据给定主题与要点，生成一篇约 1500 字的技术博客草稿，结构清晰、可后续编辑。", "task_type": "文档", "reward_points": 65, "location": "远程", "duration_estimate": "~1.5h", "skills": ["写作", "技术"]},
    {"title": "用户反馈分类与标签（200 条）", "description": "对 200 条用户反馈按类型、优先级打标签，输出结构化表格，便于产品排期。", "task_type": "数据分析", "reward_points": 40, "location": "远程", "duration_estimate": "~1.5h", "skills": ["数据标注", "分类"]},
    {"title": "REST API 接口文档生成", "description": "根据现有代码或 OpenAPI 草稿，生成完整的 REST API 文档（含请求/响应示例）。", "task_type": "文档", "reward_points": 60, "location": "远程", "duration_estimate": "~2h", "skills": ["API", "文档"]},
    {"title": "E2E 测试用例（登录与核心流程）", "description": "为 Web 应用编写 3～5 个 E2E 测试（Playwright 或 Cypress），覆盖登录与核心业务流程。", "task_type": "测试", "reward_points": 75, "location": "远程", "duration_estimate": "~2.5h", "skills": ["E2E", "Playwright"]},
    {"title": "周度数据看板指标说明", "description": "根据现有数据看板，撰写一份 1 页的指标说明文档（含口径与使用建议）。", "task_type": "文档", "reward_points": 35, "location": "远程", "duration_estimate": "~1h", "skills": ["文档", "指标"]},
    {"title": "行业白皮书摘要（约 20 页）", "description": "阅读给定行业白皮书约 20 页，输出执行摘要与关键结论（约 800 字）。", "task_type": "调研", "reward_points": 70, "location": "远程", "duration_estimate": "~2h", "skills": ["调研", "摘要"]},
]


def seed():
    init_db()
    db = SessionLocal()
    try:
        # 1. 创建用户（若已存在则跳过）
        user_map = {}
        for u in USERS:
            existing = db.query(User).filter(User.username == u["username"]).first()
            if existing:
                user_map[u["username"]] = existing
                print(f"  user exists: {u['username']}")
                continue
            user = User(
                username=u["username"],
                email=u["email"],
                hashed_password=get_password_hash(DEMO_PASSWORD),
                is_active=True,
                credits=500,
            )
            db.add(user)
            db.flush()
            user_map[u["username"]] = user
            print(f"  created user: {u['username']} (id={user.id})")
        db.commit()

        # 2. 创建 Agent（若同名+同一 owner 已存在则跳过）
        agent_map = []
        for a in AGENTS:
            owner = user_map[a["owner_username"]]
            existing = db.query(Agent).filter(Agent.name == a["name"], Agent.owner_id == owner.id).first()
            if existing:
                agent_map.append(existing)
                print(f"  agent exists: {a['name']} (@{a['owner_username']})")
                continue
            agent = Agent(
                name=a["name"],
                description=a["description"],
                agent_type=a["agent_type"],
                owner_id=owner.id,
                is_active=True,
            )
            db.add(agent)
            db.flush()
            agent_map.append(agent)
            print(f"  created agent: {a['name']} (@{a['owner_username']}) (id={agent.id})")
        db.commit()

        # 3. 创建任务（以 alice 为发布者，部分开放、部分指定接取）
        alice = user_map["alice"]
        for i, t in enumerate(TASKS):
            # 检查是否已有相同标题的任务（同 owner）
            existing = db.query(Task).filter(Task.title == t["title"], Task.owner_id == alice.id).first()
            if existing:
                print(f"  task exists: {t['title']}")
                continue
            # 部分任务指定接取者：前 2 个任务指定前 2 个 agent
            invited_ids = None
            if i < 2 and len(agent_map) >= 2:
                invited_ids = [agent_map[0].id, agent_map[1].id]
            extra = {}
            if t.get("location"):
                extra["location"] = t["location"]
            if t.get("duration_estimate"):
                extra["duration_estimate"] = t["duration_estimate"]
            if t.get("skills"):
                extra["skills"] = t["skills"]
            task = Task(
                title=t["title"],
                description=t["description"],
                status="open",
                priority="medium",
                task_type=t["task_type"],
                owner_id=alice.id,
                reward_points=t["reward_points"],
                invited_agent_ids=invited_ids,
                input_data=extra if extra else None,
            )
            db.add(task)
            print(f"  created task: {t['title']} (reward={t['reward_points']})")
        db.commit()
        print("Seed completed.")
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
