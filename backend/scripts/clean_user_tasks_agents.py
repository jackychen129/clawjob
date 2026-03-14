#!/usr/bin/env python3
"""
清理指定用户（如 chen zheng）发布的所有任务与智能体。
用法：
  CLEAN_USERNAME="chen zheng" PYTHONPATH=. python scripts/clean_user_tasks_agents.py
  # 或匹配用户名包含某关键词（逗号分隔）
  CLEAN_USERNAME="chen,zheng" PYTHONPATH=. python scripts/clean_user_tasks_agents.py
  DRY_RUN=1 仅预览不删除。
"""
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.database.relational_db import SessionLocal, User, Task, Agent


def main():
    raw = os.environ.get("CLEAN_USERNAME", "").strip()
    if not raw:
        print("Usage: CLEAN_USERNAME='chen zheng' PYTHONPATH=. python scripts/clean_user_tasks_agents.py")
        print("       Or CLEAN_USERNAME='chen,zheng' to match any username containing either.")
        sys.exit(1)
    dry_run = os.environ.get("DRY_RUN", "").strip() == "1"
    # 支持精确或逗号分隔关键词（任一匹配即清理）
    parts = [p.strip().lower() for p in raw.replace("，", ",").split(",") if p.strip()]
    db = SessionLocal()
    try:
        users_to_clean = []
        for u in db.query(User).all():
            uname = (u.username or "").lower()
            if not uname:
                continue
            if raw.strip().lower() == uname:
                users_to_clean.append(u)
            elif parts and any(p in uname for p in parts):
                users_to_clean.append(u)
        if not users_to_clean:
            print("No users matched.")
            return
        for u in users_to_clean:
            print(f"User: id={u.id} username={u.username}")
        tasks_deleted = 0
        agents_deleted = 0
        for u in users_to_clean:
            for t in db.query(Task).filter(Task.owner_id == u.id).all():
                print(f"  {'[DRY RUN] would delete task' if dry_run else 'deleted task'} id={t.id} title={t.title[:50]!r}")
                if not dry_run:
                    db.delete(t)
                tasks_deleted += 1
            for a in db.query(Agent).filter(Agent.owner_id == u.id).all():
                print(f"  {'[DRY RUN] would delete agent' if dry_run else 'deleted agent'} id={a.id} name={a.name}")
                if not dry_run:
                    db.delete(a)
                agents_deleted += 1
        if (tasks_deleted or agents_deleted) and not dry_run:
            db.commit()
        print(f"Done. {'Would delete' if dry_run else 'Deleted'} {tasks_deleted} task(s), {agents_deleted} agent(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
