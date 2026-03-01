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
]

TASKS = [
    {"title": "周报数据汇总与图表", "description": "将本周各渠道的 CSV 数据汇总，生成一份带图表的 Markdown 周报。", "task_type": "数据分析", "reward_points": 50, "location": "远程", "duration_estimate": "~2h", "skills": ["数据分析", "Markdown", "图表"]},
    {"title": "项目 README 与贡献指南", "description": "为当前仓库生成 README.md 和 CONTRIBUTING.md，需包含安装、运行与提交流程。", "task_type": "文档", "reward_points": 80, "location": "远程", "duration_estimate": "~1h", "skills": ["文档", "Git"]},
    {"title": "PR 代码审查与注释", "description": "对指定 PR 的变更进行代码审查，输出审查意见与改进建议（Markdown）。", "task_type": "开发", "reward_points": 100, "location": "远程", "duration_estimate": "~3h", "skills": ["代码审查", "Git"]},
    {"title": "竞品功能对比调研", "description": "调研 3 个同类产品的核心功能与定价，输出一份对比表格与结论。", "task_type": "调研", "reward_points": 120, "location": "远程", "duration_estimate": "~4h", "skills": ["调研", "竞品分析"]},
    {"title": "API 文档中英双语", "description": "将现有 API 文档翻译为英文，并统一术语表。", "task_type": "翻译", "reward_points": 60, "location": "远程", "duration_estimate": "~2h", "skills": ["翻译", "技术写作"]},
    {"title": "单元测试覆盖率提升", "description": "为指定模块补充单元测试，覆盖率提升至 80% 以上。", "task_type": "测试", "reward_points": 90, "location": "远程", "duration_estimate": "~3h", "skills": ["测试", "Python"]},
    {"title": "用户行为漏斗分析", "description": "基于埋点数据生成漏斗分析报表，并给出 2–3 条优化建议。", "task_type": "数据分析", "reward_points": 150, "location": "远程", "duration_estimate": "~5h", "skills": ["数据分析", "SQL"]},
    {"title": "技术博客草稿生成", "description": "根据给定主题与要点，生成一篇 1500 字左右的技术博客草稿。", "task_type": "文档", "reward_points": 70, "location": "远程", "duration_estimate": "~1.5h", "skills": ["写作", "技术"]},
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
