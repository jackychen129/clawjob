#!/usr/bin/env python3
"""
ClawJob 新手 Quest 种子脚本（运维专用，幂等）

创建 3 条零奖励 onboarding 任务（input_data.onboarding=true）。
**不会**自动在生产环境运行；须显式传入 --apply。

用法：
  PYTHONPATH=. python backend/scripts/seed_onboarding_quest.py
  PYTHONPATH=. python backend/scripts/seed_onboarding_quest.py --apply
"""
import argparse
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.database.relational_db import SessionLocal, init_db
from app.services.onboarding_quest import seed_onboarding_quest_tasks


def main():
    parser = argparse.ArgumentParser(description="Seed platform onboarding quest tasks (ops only).")
    parser.add_argument("--apply", action="store_true", help="Actually insert tasks.")
    args = parser.parse_args()
    apply = args.apply or os.getenv("CLAWJOB_SEED_ONBOARDING_QUEST", "").strip() in ("1", "true", "yes")
    if not apply:
        print("Dry-run mode (pass --apply or CLAWJOB_SEED_ONBOARDING_QUEST=1 to write).")
    init_db()
    db = SessionLocal()
    try:
        n = seed_onboarding_quest_tasks(db, apply=apply)
        print(f"Done: {n} onboarding task(s) {'created' if apply else 'would be created'}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
