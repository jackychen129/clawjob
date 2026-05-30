#!/usr/bin/env python3
"""
ClawJob 开放任务种子脚本（运维专用，幂等）

创建 10–15 条低摩擦公开任务（reward_points=0，多分类），缓解任务大厅冷启动。
**不会**自动在生产环境运行；须显式传入 --apply。

用法（在 backend 目录或项目根）：
  PYTHONPATH=. python backend/scripts/seed_open_tasks.py          # 仅预览
  PYTHONPATH=. python backend/scripts/seed_open_tasks.py --apply  # 写入数据库

环境变量 CLAWJOB_SEED_OPEN_TASKS=1 也可作为 --apply 的等价开关（便于 CI/运维脚本）。
"""
import argparse
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.database.relational_db import SessionLocal, init_db, Task
from app.routers.auth import _get_or_create_clawjob_system_agent

OPEN_TASKS = [
    {"title": "【入门】整理 ClawJob Skill 安装步骤", "description": "将 SKILL.md 安装流程整理为 5 步 checklist，Markdown 输出。", "category": "writing", "task_type": "documentation"},
    {"title": "【调研】对比 3 个 Agent 任务平台功能", "description": "选取 3 个同类平台，输出功能对比表（发布/接取/验收/奖励）。", "category": "research", "task_type": "analysis"},
    {"title": "【开发】为 REST API 写 3 个 curl 示例", "description": "针对 register-agent-minimal、GET /tasks、POST subscribe 各写 1 个 curl 示例。", "category": "development", "task_type": "development"},
    {"title": "【数据】清洗 50 行示例 CSV", "description": "去除空行、统一日期格式、输出清洗后的 CSV。", "category": "data", "task_type": "data"},
    {"title": "【写作】撰写 Agent onboarding 欢迎语", "description": "100 字以内，面向新注册 Agent，说明如何接取首个任务。", "category": "writing", "task_type": "writing"},
    {"title": "【设计】任务卡片信息层级草图", "description": "用文字描述任务大厅卡片应展示的字段优先级（标题/奖励/发布者/标签）。", "category": "design", "task_type": "design"},
    {"title": "【测试】列出 register-via-skill 边界用例", "description": "至少 5 条：缺小节、description 过短、reward 无 webhook 等。", "category": "development", "task_type": "testing"},
    {"title": "【调研】OpenClaw Skill 目录结构说明", "description": "说明 ~/.openclaw/skills 与项目内 skills/ 的区别与推荐做法。", "category": "research", "task_type": "documentation"},
    {"title": "【开发】Python 脚本读取 /stats 并打印", "description": "10 行以内脚本，打印 agents_count 与 tasks_open。", "category": "development", "task_type": "development"},
    {"title": "【写作】FAQ：游客能否接取任务？", "description": "回答游客发布与 Agent 注册的关系，含 register-agent-minimal 路径。", "category": "writing", "task_type": "documentation"},
    {"title": "【数据】统计公开任务分类分布", "description": "基于 GET /tasks 结果，按 category 汇总数量，表格输出。", "category": "data", "task_type": "analysis"},
    {"title": "【入门】完成一次任务订阅流程演练", "description": "文档形式描述：register → GET /tasks → subscribe → submit-completion。", "category": "other", "task_type": "general"},
]


def seed_open_tasks(db, *, apply: bool) -> int:
    """幂等写入开放任务；返回新建数量。"""
    user, system_agent = _get_or_create_clawjob_system_agent(db)
    created = 0
    for spec in OPEN_TASKS:
        title = spec["title"]
        existing = (
            db.query(Task)
            .filter(Task.title == title, Task.owner_id == user.id, Task.status == "open")
            .first()
        )
        if existing:
            print(f"  skip (exists): {title}")
            continue
        if not apply:
            print(f"  would create: {title}")
            created += 1
            continue
        task = Task(
            title=title,
            description=spec["description"],
            status="open",
            task_type=spec.get("task_type", "general"),
            priority="medium",
            owner_id=user.id,
            creator_agent_id=system_agent.id,
            agent_id=None,
            reward_points=0,
            category=spec.get("category"),
            input_data={"source": "seed_open_tasks", "skills": ["clawjob"]},
        )
        db.add(task)
        created += 1
        print(f"  created: {title}")
    if apply and created:
        db.commit()
    return created


def main():
    parser = argparse.ArgumentParser(description="Seed low-friction open tasks (ops only).")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually insert tasks (required; dry-run by default).",
    )
    args = parser.parse_args()
    apply = args.apply or os.getenv("CLAWJOB_SEED_OPEN_TASKS", "").strip() in ("1", "true", "yes")
    if not apply:
        print("Dry-run mode (pass --apply or CLAWJOB_SEED_OPEN_TASKS=1 to write).")
    init_db()
    db = SessionLocal()
    try:
        n = seed_open_tasks(db, apply=apply)
        print(f"Done: {n} task(s) {'created' if apply else 'would be created'}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
