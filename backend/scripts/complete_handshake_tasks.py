#!/usr/bin/env python3
"""
将 Skill 注册产生的「握手」任务标记为已完成（运维修复历史数据）。

匹配规则（任一）：
- title ILIKE %handshake%
- title ILIKE %握手%
- description 含「握手任务」（与 register_via_skill 首条任务文案一致）

用法（容器内）：
  cd /app && PYTHONPATH=. python3 scripts/complete_handshake_tasks.py
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.database.relational_db import SessionLocal, Task, init_db


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        q = (
            db.query(Task)
            .filter(Task.status != "completed")
            .filter(
                or_(
                    Task.title.ilike("%handshake%"),
                    Task.title.ilike("%握手%"),
                    Task.description.ilike("%握手任务%"),
                )
            )
        )
        rows = q.all()
        now = datetime.utcnow()
        n = 0
        for t in rows:
            t.status = "completed"
            t.completed_at = t.completed_at or now
            t.submitted_at = t.submitted_at or now
            od = t.output_data if isinstance(t.output_data, dict) else {}
            if not od.get("result_summary"):
                od = {**od, "result_summary": "握手任务已由平台标记为已完成（运维脚本）。"}
                t.output_data = od
            n += 1
        db.commit()
        print(f"complete_handshake_tasks: updated {n} row(s)")
        for t in rows:
            print(f"  task_id={t.id} title={t.title[:60]!r} status={t.status}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
