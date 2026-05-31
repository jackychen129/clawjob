"""审计所有 Agent，标记 system / guest / probe / demo 等非真实数据特征。

用法（backend 目录）:
  python3 scripts/audit_agents.py
  python3 scripts/audit_agents.py --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.database.relational_db import Agent, SessionLocal, User  # noqa: E402
from app.domain.agent_public import (  # noqa: E402
    agent_completed_stats,
    agent_is_public,
    agent_subscription_count,
    audit_agent_flags,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit agents for non-real flags")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    db = SessionLocal()
    rows_out = []
    summary = {
        "total": 0,
        "public": 0,
        "non_public": 0,
        "flag_counts": {},
    }
    try:
        agents = db.query(Agent).order_by(Agent.id).all()
        owners: dict[int, User | None] = {}
        for agent in agents:
            if agent.owner_id not in owners:
                owners[agent.owner_id] = (
                    db.query(User).filter(User.id == agent.owner_id).first()
                )
            owner = owners[agent.owner_id]
            completed, earned = agent_completed_stats(db, agent.id)
            subs = agent_subscription_count(db, agent.id)
            flags = audit_agent_flags(
                agent,
                owner,
                completed_count=completed,
                earned_points=earned,
                subscription_count=subs,
            )
            is_public = agent_is_public(agent, owner)
            summary["total"] += 1
            if is_public:
                summary["public"] += 1
            else:
                summary["non_public"] += 1
            for k, v in flags.items():
                if v:
                    summary["flag_counts"][k] = summary["flag_counts"].get(k, 0) + 1
            rows_out.append(
                {
                    "id": agent.id,
                    "name": agent.name,
                    "owner": getattr(owner, "username", None),
                    "is_active": bool(agent.is_active),
                    "is_public": is_public,
                    "completed_tasks": completed,
                    "earned_points": earned,
                    "subscriptions": subs,
                    "flags": flags,
                }
            )
    finally:
        db.close()

    if args.json:
        print(json.dumps({"summary": summary, "agents": rows_out}, ensure_ascii=False, indent=2))
    else:
        print(f"Total agents: {summary['total']}")
        print(f"Public (real): {summary['public']}")
        print(f"Non-public:    {summary['non_public']}")
        print("Flag counts:")
        for k, v in sorted(summary["flag_counts"].items()):
            print(f"  {k}: {v}")
        print("\nNon-public agents:")
        for row in rows_out:
            if row["is_public"]:
                continue
            active_flags = [k for k, v in row["flags"].items() if v]
            print(
                f"  id={row['id']} name={row['name']!r} owner={row['owner']!r} "
                f"flags={active_flags} completed={row['completed_tasks']} earned={row['earned_points']}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
