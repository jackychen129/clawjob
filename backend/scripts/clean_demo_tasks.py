#!/usr/bin/env python3
"""Clean demo tasks by title. Run: PYTHONPATH=. python scripts/clean_demo_tasks.py. Set DRY_RUN=1 to preview."""
import os
import sys
_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)
from app.database.relational_db import SessionLocal, Task

DEMO_TASK_TITLES = [
    "周报数据汇总与图表", "项目 README 与贡献指南", "PR 代码审查与注释",
    "竞品功能对比调研", "API 文档中英双语", "单元测试覆盖率提升",
    "用户行为漏斗分析", "技术博客草稿生成",
]

def main():
    dry_run = os.environ.get("DRY_RUN", "").strip() == "1"
    db = SessionLocal()
    try:
        deleted = 0
        for title in DEMO_TASK_TITLES:
            for t in db.query(Task).filter(Task.title == title).all():
                print(f"{'[DRY RUN] would delete' if dry_run else 'deleted'} id={t.id} title={t.title}")
                if not dry_run:
                    db.delete(t)
                deleted += 1
        if deleted and not dry_run:
            db.commit()
        print(f"Done. {'Would delete' if dry_run else 'Deleted'} {deleted} task(s).")
    finally:
        db.close()

if __name__ == "__main__":
    main()
