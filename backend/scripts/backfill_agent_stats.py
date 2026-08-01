#!/usr/bin/env python3
"""Backfill agent_stats + tasks.is_public_listing."""
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.database.relational_db import SessionLocal, Task, User, init_db
from app.domain.task_helpers import sync_task_public_listing
from app.services.agent_stats import backfill_all_agent_stats


def backfill_task_listing(db, batch_size: int = 500) -> int:
    updated = 0
    offset = 0
    while True:
        rows = db.query(Task, User).join(User, Task.owner_id == User.id).order_by(Task.id).offset(offset).limit(batch_size).all()
        if not rows:
            break
        for task, owner in rows:
            pub = sync_task_public_listing(task, owner)
            if bool(getattr(task, "is_public_listing", False)) != pub:
                updated += 1
        db.commit()
        offset += batch_size
        if len(rows) < batch_size:
            break
    return updated


def main() -> int:
    init_db()
    db = SessionLocal()
    try:
        n_stats = backfill_all_agent_stats(db)
        n_tasks = backfill_task_listing(db)
        print(f"agent_stats rows: {n_stats}, task listing flags updated: {n_tasks}")
        from app.services.platform_stats_cache import invalidate_platform_stats_cache

        invalidate_platform_stats_cache()
        print("platform stats cache invalidated")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
