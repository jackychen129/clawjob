#!/usr/bin/env python3
"""Backfill agents.is_public from visibility rules. Run after 007 migration."""
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.database.relational_db import SessionLocal, init_db
from app.domain.agent_helpers import ensure_agents_is_public_column
from app.domain.agent_public import backfill_all_agent_is_public


def main() -> int:
    init_db()
    ensure_agents_is_public_column()
    db = SessionLocal()
    try:
        n = backfill_all_agent_is_public(db, batch_size=500)
        print(f"Updated {n} agent is_public flags.")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
