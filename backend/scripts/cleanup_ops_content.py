"""删除运营 Agent / 平台种子发布的任务与社区运营帖，保留外部三方 Agent 任务与真实社区讨论。

命中并删除：
- 社区：运营日报 / ops_report / ClawJob-Ops 自动化 recap（与 community_public_filter 一致）
- 任务：clawjob_system 发布、seed_open_tasks、seed_demo、演示账号、内部探活标题等

用法（backend 目录）：
  python3 scripts/cleanup_ops_content.py              # dry-run
  python3 scripts/cleanup_ops_content.py --apply      # 写库删除
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

from app.database.relational_db import (  # noqa: E402
    Agent,
    ChatDispatchLog,
    ChatMessage,
    Conversation,
    ExecutionRun,
    ExecutionStep,
    InternalMessage,
    PlatformCommissionRecord,
    SafetyEvent,
    SessionLocal,
    SkillRevenueShare,
    Task,
    TaskBid,
    TaskComment,
    TaskSubscription,
    User,
    UserCommissionRecord,
)
from app.domain.agent_public import agent_is_system_agent, owner_is_guest, owner_is_system  # noqa: E402
from app.domain.task_helpers import task_title_looks_internal  # noqa: E402
from app.services.community_public_filter import is_ops_internal_message  # noqa: E402

_OPS_AUTHOR_NAME_RE = re.compile(r"clawjob[-_\s]?ops", re.I)

# NOTE: seed_onboarding_quest is intentionally NOT listed — onboarding quests
# must survive cleanup so new Agents always have a first-quest path.
_SEED_TASK_SOURCES = frozenset({
    "seed_open_tasks",
    "seed_demo_data",
    "script",
    "verify-deployed",
    "monitor_probe",
})

_DEMO_TASK_TITLES = frozenset({
    "周报数据汇总与图表", "项目 README 与贡献指南", "PR 代码审查与注释",
    "竞品功能对比调研", "API 文档中英双语", "单元测试覆盖率提升",
    "用户行为漏斗分析", "技术博客草稿生成",
    "图像分类标注（500 张）", "客服工单摘要（10 条）", "登录模块单元测试",
    "竞品功能与定价对比（3 款）", "产品页文案中译英", "API 集成测试脚本",
    "用户反馈分类与标签（200 条）", "REST API 接口文档生成",
    "E2E 测试用例（登录与核心流程）", "周度数据看板指标说明", "行业白皮书摘要（约 20 页）",
})


def _ops_agent_ids() -> set[int]:
    raw = os.getenv("CLAWJOB_OPS_AGENT_IDS", "103").strip()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids or {103}


def _collect_ops_agents(db) -> tuple[set[int], set[int]]:
    """返回 (ops_agent_ids, ops_owner_user_ids)。"""
    ops_ids = set(_ops_agent_ids())
    ops_owner_ids: set[int] = set()
    for agent in db.query(Agent).all():
        name = (agent.name or "").strip()
        if int(agent.id) in ops_ids or (_OPS_AUTHOR_NAME_RE.search(name) if name else False):
            ops_ids.add(int(agent.id))
            ops_owner_ids.add(int(agent.owner_id))
    return ops_ids, ops_owner_ids


def _is_onboarding_quest_task(task: Task) -> bool:
    """Platform first-quest tasks must never be deleted by ops cleanup."""
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    source = (extra.get("source") or "").strip()
    title = (task.title or "").strip()
    if extra.get("onboarding") is True:
        return True
    if source == "seed_onboarding_quest":
        return True
    if title.startswith("【新手 Quest"):
        return True
    return False


def _task_delete_reason(
    task: Task,
    owner: User | None,
    creator: Agent | None,
    ops_agent_ids: set[int],
    ops_owner_ids: set[int],
) -> str | None:
    extra = task.input_data if isinstance(task.input_data, dict) else {}
    source = (extra.get("source") or "").strip()
    title = (task.title or "").strip()
    title_l = title.lower()

    if _is_onboarding_quest_task(task):
        return None

    if "registration handshake" in title_l:
        return "registration handshake"
    for needle in (
        "验证部署", "e2e 验证", "deploy smoke", "测试任务：验证",
        "测试 openclaw", "测试openclaw", "smoke second task",
    ):
        if needle in title_l or needle in (task.description or "").lower():
            return f"internal pattern ({needle})"

    if source == "register_via_skill_second":
        return "register_via_skill_second probe"
    if source == "register_via_skill":
        if task_title_looks_internal(title, task.description or ""):
            return "register_via_skill internal"
    if source in _SEED_TASK_SOURCES:
        return f"seed source={source}"
    if extra.get("hidden_from_public") and source:
        return f"hidden seed/internal source={source}"
    if owner and owner_is_system(getattr(owner, "username", None)):
        return "owner=clawjob_system"
    if owner and int(owner.id) in ops_owner_ids:
        return "owner=ops account"
    if creator and int(creator.id) in ops_agent_ids:
        return f"creator=ops agent #{creator.id}"
    if task_title_looks_internal(title, task.description or ""):
        return "internal title pattern"
    if title in _DEMO_TASK_TITLES:
        return "demo seed title"
    if title.startswith("【入门】") or title.startswith("【展示】") or title.startswith("【Agent 直连展示】"):
        return "platform showcase title"
    if owner and owner_is_guest(getattr(owner, "username", None)):
        if any(w in title_l for w in ("测试", "test", "验证", "verify", "e2e")):
            return "guest test/verify task"
    if owner:
        uname = (owner.username or "").strip()
        email = (owner.email or "").strip().lower()
        if uname in {"alice", "bob", "carol"} and email.endswith("@example.com"):
            return f"demo user publisher {uname}"
    if creator and owner:
        if agent_is_system_agent(creator, owner):
            return "system agent publisher"
    return None


def _delete_message_tree(db, msg_id: int, *, apply: bool) -> int:
    deleted = 0
    replies = db.query(ChatMessage).filter(ChatMessage.reply_to_id == msg_id).all()
    for reply in replies:
        deleted += _delete_message_tree(db, int(reply.id), apply=apply)
    msg = db.query(ChatMessage).filter(ChatMessage.id == msg_id).first()
    if not msg:
        return deleted
    deleted += 1
    preview = (msg.content_md or "")[:60].replace("\n", " ")
    print(f"  [{'apply' if apply else 'dry-run'}] delete message id={msg_id} preview={preview!r}")
    if apply:
        db.query(ChatDispatchLog).filter(ChatDispatchLog.message_id == msg_id).delete(synchronize_session=False)
        db.delete(msg)
    return deleted


def _delete_task_tree(db, task_id: int, *, apply: bool) -> int:
    deleted = 0
    for sub in db.query(Task).filter(Task.parent_task_id == task_id).all():
        deleted += _delete_task_tree(db, int(sub.id), apply=apply)
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return deleted
    deleted += 1
    print(
        f"  [{'apply' if apply else 'dry-run'}] delete task id={task_id} "
        f"status={task.status} title={(task.title or '')[:70]!r}"
    )
    if apply:
        db.query(TaskSubscription).filter(TaskSubscription.task_id == task_id).delete(synchronize_session=False)
        db.query(TaskComment).filter(TaskComment.task_id == task_id).delete(synchronize_session=False)
        db.query(TaskBid).filter(TaskBid.task_id == task_id).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.task_id == task_id).delete(synchronize_session=False)
        db.query(ExecutionStep).filter(ExecutionStep.task_id == task_id).delete(synchronize_session=False)
        db.query(ExecutionRun).filter(ExecutionRun.task_id == task_id).delete(synchronize_session=False)
        db.query(SafetyEvent).filter(SafetyEvent.related_task_id == task_id).delete(synchronize_session=False)
        db.query(InternalMessage).filter(InternalMessage.related_task_id == task_id).delete(synchronize_session=False)
        db.query(PlatformCommissionRecord).filter(PlatformCommissionRecord.task_id == task_id).delete(synchronize_session=False)
        db.query(UserCommissionRecord).filter(UserCommissionRecord.task_id == task_id).delete(synchronize_session=False)
        db.query(SkillRevenueShare).filter(SkillRevenueShare.related_task_id == task_id).delete(synchronize_session=False)
        db.delete(task)
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete ops/seed platform content from production DB")
    parser.add_argument("--apply", action="store_true", help="Actually delete (default dry-run)")
    args = parser.parse_args()
    apply = bool(args.apply)

    db = SessionLocal()
    ops_agent_ids, ops_owner_ids = _collect_ops_agents(db)
    print(f"Ops agents: {sorted(ops_agent_ids)}; ops owner users: {sorted(ops_owner_ids)}")

    owners: dict[int, User | None] = {}
    agents: dict[int, Agent | None] = {}

    msg_deleted = 0
    for msg in db.query(ChatMessage).order_by(ChatMessage.id).all():
        if msg.author_agent_id not in agents:
            agents[msg.author_agent_id] = db.query(Agent).filter(Agent.id == msg.author_agent_id).first()
        author = agents[msg.author_agent_id]
        author_is_ops = author is not None and int(author.id) in ops_agent_ids
        if not author_is_ops and not is_ops_internal_message(msg, author):
            continue
        reason = "ops agent author" if author_is_ops else "ops internal content"
        print(f"[message match] id={msg.id} reason={reason}")
        msg_deleted += _delete_message_tree(db, int(msg.id), apply=apply)

    task_deleted = 0
    task_ids = [row[0] for row in db.query(Task.id).order_by(Task.id).all()]
    for task_id in task_ids:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            continue
        if task.owner_id not in owners:
            owners[task.owner_id] = db.query(User).filter(User.id == task.owner_id).first()
        owner = owners[task.owner_id]
        creator = None
        if task.creator_agent_id:
            if task.creator_agent_id not in agents:
                agents[task.creator_agent_id] = db.query(Agent).filter(Agent.id == task.creator_agent_id).first()
            creator = agents[task.creator_agent_id]
        reason = _task_delete_reason(task, owner, creator, ops_agent_ids, ops_owner_ids)
        if not reason:
            continue
        print(f"[task match] id={task_id} reason={reason}")
        task_deleted += _delete_task_tree(db, task_id, apply=apply)

    if apply:
        db.commit()
        print(f"\n已提交：删除 {msg_deleted} 条社区消息、{task_deleted} 条任务。")
    else:
        print(
            f"\nDry-run：将删除 {msg_deleted} 条社区消息、{task_deleted} 条任务。"
            f"\n执行 python3 scripts/cleanup_ops_content.py --apply 以写库。"
        )
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
