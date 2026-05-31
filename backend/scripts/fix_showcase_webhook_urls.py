#!/usr/bin/env python3
"""
将展示任务（input_data.showcase）中误配的 /health 完成回调改为 showcase-completion webhook。

用法：
  cd backend && python3 scripts/fix_showcase_webhook_urls.py          # dry-run
  cd backend && python3 scripts/fix_showcase_webhook_urls.py --apply
"""
import argparse
import os
import sys

_backend = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from app.database.relational_db import SessionLocal, init_db, Task

NEW_URL = os.getenv(
    "CLAWJOB_SHOWCASE_WEBHOOK_URL",
    "https://api.clawjob.com.cn/webhooks/showcase-completion",
).strip()
OLD_SUFFIX = "/health"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write changes to DB")
    args = parser.parse_args()
    init_db()
    db = SessionLocal()
    try:
        rows = db.query(Task).filter(Task.completion_webhook_url.isnot(None)).all()
        updated = 0
        for t in rows:
            url = (t.completion_webhook_url or "").strip()
            inp = t.input_data if isinstance(t.input_data, dict) else {}
            is_showcase = inp.get("showcase") in (True, "true", "True", "1", 1)
            if not is_showcase and not url.rstrip("/").endswith(OLD_SUFFIX):
                continue
            if url.rstrip("/").endswith(OLD_SUFFIX) or (is_showcase and url != NEW_URL):
                print(f"  task #{t.id} {t.title!r}: {url!r} -> {NEW_URL!r}")
                if args.apply:
                    t.completion_webhook_url = NEW_URL
                    updated += 1
        if args.apply and updated:
            db.commit()
        print(f"Done: {updated} task(s) {'updated' if args.apply else 'would update'}.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
