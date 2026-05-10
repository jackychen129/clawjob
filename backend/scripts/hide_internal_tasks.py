"""回填脚本：将历史上非真实的任务标记为 hidden_from_public，使其不再进入公开任务大厅。

命中规则（任一即标记）：
1. 所有者为平台引导账号 `clawjob_system`；
2. `input_data.source == "register_via_skill"`（即注册自动写入的握手任务）；
3. 标题命中部署校验 / 模拟脚本 / 明显测试占位词（如 "verify", "smoke", "deploy",
   "【verify】", "自动验证", "验证部署"）；
4. 描述过短（< 40 字符）且标题包含 “test/验证” 字样。

用法（从 backend/ 目录）：
    python3 scripts/hide_internal_tasks.py            # 试运行，列出将被标记的任务 id
    APPLY=1 python3 scripts/hide_internal_tasks.py    # 实际写库
"""
from __future__ import annotations

import os
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import SessionLocal, Task, User  # noqa: E402


PLACEHOLDER_TITLE_TOKENS = (
    "verify", "smoke", "deploy",
    "【verify】", "[verify]",
    "【test】", "[test]",
    "【smoke】", "[smoke]",
    "【demo】", "[demo]",
    "【e2e】", "[e2e]", "e2e_", "e2e-",
    "自动验证", "验证部署", "部署验证", "验证部署任务",
    "测试 openclaw", "测试openclaw",
    "clawjob registration handshake",
    "sim-task-", "sim-slow-", "sim-cancel-", "sim-auction-",
    "sim-refbonus-", "sim-rec-", "sim-submitpii-", "rfq-a-", "rfq-b-", "rfq-c-",
    "rfq-bad-",
)


def should_hide(task: Task, owner: User | None) -> tuple[bool, str]:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    if isinstance(extra, dict):
        if extra.get("hidden_from_public"):
            return False, "already hidden"
        if (extra.get("source") or "").strip() == "register_via_skill":
            return True, "handshake (source=register_via_skill)"
    if owner is not None and owner.username == "clawjob_system":
        return True, "owned by clawjob_system"
    title_l = (task.title or "").lower()
    for tok in PLACEHOLDER_TITLE_TOKENS:
        if tok.lower() in title_l:
            return True, f"title contains placeholder token '{tok}'"
    desc = (task.description or "").strip()
    if len(desc) < 40 and any(
        w in title_l for w in ("test", "验证", "测试", "demo", "smoke")
    ):
        return True, "short desc + test-like title"
    return False, ""


def main() -> int:
    apply = os.environ.get("APPLY", "").lower() in ("1", "true", "yes")
    db = SessionLocal()
    total_matched = 0
    try:
        owners: dict[int, User] = {}
        for t in db.query(Task).yield_per(500):
            if t.owner_id not in owners:
                owners[t.owner_id] = (
                    db.query(User).filter(User.id == t.owner_id).first()
                )
            hide, reason = should_hide(t, owners[t.owner_id])
            if not hide:
                continue
            total_matched += 1
            data = dict(t.input_data or {}) if isinstance(t.input_data, dict) else {}
            data["hidden_from_public"] = True
            data["hidden_reason"] = reason
            data["hidden_at"] = datetime.utcnow().isoformat() + "Z"
            print(f"[hide] task_id={t.id} status={t.status} title={t.title!r} reason={reason}")
            if apply:
                t.input_data = data
                flag_modified(t, "input_data")
        if apply:
            db.commit()
            print(f"\n已提交：{total_matched} 条任务被标记为 hidden_from_public。")
        else:
            print(
                f"\n匹配 {total_matched} 条任务（试运行）。执行 APPLY=1 python3 scripts/hide_internal_tasks.py 以写库。"
            )
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
