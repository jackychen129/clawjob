"""清理非真实 Agent：默认 dry-run；--apply 写库（停用 + hidden_from_public）。

不会停用/隐藏有真实完成任务或收益的 Agent。
系统引导 Agent 仅标记 hidden_from_public，保持 is_active=true。

用法（backend 目录）:
  python3 scripts/cleanup_non_real_agents.py
  python3 scripts/cleanup_non_real_agents.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import Agent, SessionLocal, User  # noqa: E402
from app.domain.agent_public import (  # noqa: E402
    agent_completed_stats,
    agent_is_system_agent,
    audit_agent_flags,
    cleanup_apply_hide,
    cleanup_should_hide,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Hide/deactivate non-real agents")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="写库（默认仅 dry-run）",
    )
    args = parser.parse_args()
    apply = bool(args.apply)

    db = SessionLocal()
    matched = 0
    skipped_protected = 0
    already_hidden = 0
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
            flags = audit_agent_flags(
                agent,
                owner,
                completed_count=completed,
                earned_points=earned,
            )
            cfg = agent.config if isinstance(agent.config, dict) else {}
            if cfg.get("hidden_from_public") and not agent.is_active:
                already_hidden += 1
                continue

            should, reason = cleanup_should_hide(agent, owner, flags)
            if not should:
                if flags.get("has_completions") or flags.get("has_real_earnings"):
                    if any(
                        flags.get(k)
                        for k in ("probe_name_pattern", "guest_owner", "system", "created_by_script")
                    ):
                        skipped_protected += 1
                        print(
                            f"[skip-protected] id={agent.id} name={agent.name!r} "
                            f"completed={completed} earned={earned}"
                        )
                continue

            matched += 1
            is_system = agent_is_system_agent(agent, owner)
            deactivate = not is_system
            action = "hide+deactivate" if deactivate else "hide-only"
            print(
                f"[{'apply' if apply else 'dry-run'}] id={agent.id} name={agent.name!r} "
                f"owner={getattr(owner, 'username', None)!r} reason={reason} action={action}"
            )
            if apply:
                cleanup_apply_hide(agent, reason, deactivate=deactivate)
                flag_modified(agent, "config")
        if apply:
            db.commit()
            print(f"\n已提交：处理 {matched} 个 Agent。")
        else:
            print(
                f"\nDry-run：将处理 {matched} 个 Agent；"
                f"已隐藏 {already_hidden}；受保护跳过 {skipped_protected}。"
                f"\n执行 python3 scripts/cleanup_non_real_agents.py --apply 以写库。"
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
