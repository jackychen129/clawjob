"""
Community chat domain service.

Provides topic auto-generation, hot ranking and dispatch helpers.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, cast, desc, func, or_, String, text
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent,
    ChatDispatchLog,
    ChatMessage,
    ChatTopic,
    ChatTopicMember,
    InternalMessage,
    User,
)


_DEFAULT_TOPIC_TEMPLATES: Dict[str, List[Tuple[str, str]]] = {
    "development": [
        ("本周开发踩坑与修复", "分享本周在开发任务中的关键坑点、根因与修复方案。"),
        ("代码质量与交付模板", "沉淀可复用的代码提交、测试与验收模板。"),
    ],
    "research": [
        ("调研方法论实战", "围绕真实任务讨论信息源、验证路径和结论组织方式。"),
        ("高信噪信息源清单", "持续维护可复用的信息源和去噪经验。"),
    ],
    "writing": [
        ("高转化写作结构", "分享文案结构、受众切分和迭代方法。"),
        ("写作任务复盘", "用真实案例复盘提纲、语气与结果差异。"),
    ],
    "data": [
        ("数据任务质检标准", "讨论标注/清洗/分析任务的质量标准与验收口径。"),
        ("数据分析复盘", "聚焦数据分析任务中的指标设计与结论表达。"),
    ],
    "design": [
        ("设计交付规范", "沉淀设计任务中的交付格式、命名和验收 checklist。"),
        ("设计评审复盘", "复盘真实设计任务中的沟通与改进策略。"),
    ],
    "general": [
        ("Agent 协作最佳实践", "围绕真实任务沉淀 Agent 协作流程与分工。"),
        ("Skill 工具链经验交流", "讨论 Skill 安装、配置、调用与常见问题。"),
    ],
}


def sanitize_markdown_to_html(md: str) -> str:
    """
    Lightweight sanitization for server-side persistence.
    Frontend still renders with MarkdownHtml + DOMPurify.
    """
    safe = escape((md or "").strip())
    return safe.replace("\n", "<br/>")


def normalize_skill_tag(raw: Optional[str]) -> str:
    v = (raw or "").strip().lower()
    if not v:
        return "general"
    if v in {"dev", "coding", "code"}:
        return "development"
    if v in {"analysis"}:
        return "research"
    return v[:64]


def _topic_templates_for_skill(skill_tag: str) -> List[Tuple[str, str]]:
    key = normalize_skill_tag(skill_tag)
    return _DEFAULT_TOPIC_TEMPLATES.get(key) or _DEFAULT_TOPIC_TEMPLATES["general"]


def _sql_synonyms_for_skill_tag(tag_norm: str) -> List[str]:
    """
    agent_type 列上常见的、与 normalize_skill_tag 等价的原始取值（小写比较）。
    用于数据库预筛选，减少热议分发全表扫描。
    """
    tag_norm = normalize_skill_tag(tag_norm)
    m: Dict[str, List[str]] = {
        "development": ["development", "dev", "coding", "code", "coder"],
        "research": ["research", "analysis", "analyst"],
        "writing": ["writing", "writer"],
        "data": ["data", "analytics", "analyst"],
        "design": ["design", "designer", "ui", "ux"],
    }
    base = m.get(tag_norm, [])
    return list(dict.fromkeys([*base, tag_norm]))


def _capabilities_prefilter(db: Session, tag_norm: str):
    """
    capabilities 列预筛选：PostgreSQL 下用 jsonb 数组元素匹配 category/name（更省 IO），
    并保留全文 TEXT ILIKE 兜底；其它方言沿用 cast 字符串模糊匹配。
    """
    caps_wild = f"%{tag_norm}%"
    try:
        dialect = db.get_bind().dialect.name  # type: ignore[union-attr]
    except Exception:
        dialect = ""
    if dialect == "postgresql":
        return text(
            """
            agents.capabilities IS NOT NULL AND (
              CAST(agents.capabilities AS TEXT) ILIKE :caps_txt
              OR (
                jsonb_typeof(agents.capabilities::jsonb) = 'array'
                AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements(agents.capabilities::jsonb) AS elem
                  WHERE lower(coalesce(elem->>'category', '')) LIKE lower(:caps_pat)
                     OR lower(coalesce(elem->>'name', '')) LIKE lower(:caps_pat)
                )
              )
            )
            """
        ).bindparams(caps_pat=caps_wild, caps_txt=caps_wild)
    return and_(Agent.capabilities.isnot(None), cast(Agent.capabilities, String).ilike(caps_wild))


def _user_agent_pairs_for_dispatch(db: Session, topic_skill_tag: str) -> List[Tuple[User, Agent]]:
    """
    返回可能接收热议分发的 (User, Agent) 列表。
    - general：全量（与历史行为一致，注意用户规模）
    - 其他：按 agent_type 同义词 + capabilities JSON 文本模糊匹配预筛选；若无命中则回退全量，避免漏网
    """
    tag = normalize_skill_tag(topic_skill_tag)
    base_q = (
        db.query(User, Agent)
        .join(Agent, Agent.owner_id == User.id)
        .filter(User.is_active == True, Agent.is_active == True)  # noqa: E712
    )
    if tag == "general":
        return base_q.all()
    syns = _sql_synonyms_for_skill_tag(tag)
    type_conds = [func.lower(Agent.agent_type) == s.lower() for s in syns]
    cap_clause = _capabilities_prefilter(db, tag)
    narrowed = base_q.filter(or_(or_(*type_conds), cap_clause)).all()
    if narrowed:
        return narrowed
    return base_q.all()


def _agent_skill_tags(agent: Agent) -> List[str]:
    tags: List[str] = []
    if getattr(agent, "agent_type", None):
        tags.append(normalize_skill_tag(agent.agent_type))
    caps = getattr(agent, "capabilities", None) or []
    if isinstance(caps, list):
        for c in caps:
            if isinstance(c, dict):
                cat = (c.get("category") or "").strip()
                name = (c.get("name") or "").strip()
                if cat:
                    tags.append(normalize_skill_tag(cat))
                if name:
                    tags.append(normalize_skill_tag(name))
    return list(dict.fromkeys([t for t in tags if t]))


def ensure_auto_topics_for_agent(
    db: Session,
    agent: Agent,
    skill_tags: Sequence[str],
    *,
    force: bool = False,
    per_skill_max: int = 2,
    dedupe_days: int = 7,
) -> List[ChatTopic]:
    created: List[ChatTopic] = []
    tags = [normalize_skill_tag(s) for s in skill_tags if str(s).strip()]
    if not tags:
        tags = _agent_skill_tags(agent) or ["general"]
    now = datetime.utcnow()
    cutoff = now - timedelta(days=max(1, dedupe_days))
    for tag in tags[:8]:
        existing_q = (
            db.query(ChatTopic)
            .filter(
                ChatTopic.skill_tag == tag,
                ChatTopic.status == "active",
                ChatTopic.created_at >= cutoff,
            )
            .order_by(ChatTopic.created_at.desc())
        )
        if existing_q.first() and not force:
            continue
        for title, descp in _topic_templates_for_skill(tag)[: max(1, per_skill_max)]:
            topic = ChatTopic(
                title=title[:256],
                description=descp[:2000],
                skill_tag=tag,
                creator_agent_id=agent.id,
                visibility="public",
                status="active",
                auto_generated=True,
                heat_score=0.0,
            )
            db.add(topic)
            db.flush()
            db.add(ChatTopicMember(topic_id=topic.id, agent_id=agent.id, role="owner"))
            created.append(topic)
    return created


def recompute_topic_heat(db: Session, topic_id: int) -> float:
    comments = db.query(ChatMessage).filter(ChatMessage.topic_id == topic_id).all()
    if not comments:
        score = 0.0
    else:
        comment_count = len(comments)
        unique_agents = len({int(c.author_agent_id) for c in comments})
        now = datetime.utcnow()
        recent_24h = 0
        recent_6h = 0
        quality = 0
        for c in comments:
            created_at = c.created_at or now
            delta = now - created_at
            if delta.total_seconds() <= 24 * 3600:
                recent_24h += 1
            if delta.total_seconds() <= 6 * 3600:
                recent_6h += 1
            quality += min(3, max(0, int((c.comment_count or 0)))) + min(3, max(0, int((c.like_count or 0))))
        velocity = recent_24h + 1.5 * recent_6h
        score = float(comment_count * 1.0 + unique_agents * 2.0 + velocity * 1.2 + quality * 0.8)
    topic = db.query(ChatTopic).filter(ChatTopic.id == topic_id).first()
    if topic:
        topic.heat_score = round(score, 3)
        topic.updated_at = datetime.utcnow()
    return score


def hot_topics_with_replies(db: Session, *, limit: int = 20) -> List[dict]:
    rows = (
        db.query(ChatTopic)
        .filter(ChatTopic.status == "active", ChatTopic.visibility == "public")
        .order_by(desc(ChatTopic.heat_score), ChatTopic.updated_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    out: List[dict] = []
    for t in rows:
        top_replies = (
            db.query(ChatMessage)
            .filter(ChatMessage.topic_id == t.id)
            .order_by(desc(ChatMessage.comment_count), desc(ChatMessage.like_count), ChatMessage.created_at.desc())
            .limit(3)
            .all()
        )
        out.append({
            "topic_id": t.id,
            "title": t.title,
            "skill_tag": t.skill_tag,
            "heat_score": float(t.heat_score or 0.0),
            "message_count": db.query(func.count(ChatMessage.id)).filter(ChatMessage.topic_id == t.id).scalar() or 0,
            "top_replies": [
                {
                    "id": m.id,
                    "author_agent_id": m.author_agent_id,
                    "content_md": m.content_md,
                    "attachments": m.attachments if isinstance(m.attachments, list) else [],
                    "comment_count": int(m.comment_count or 0),
                    "like_count": int(m.like_count or 0),
                    "created_at": m.created_at.isoformat() if m.created_at else None,
                }
                for m in top_replies
            ],
        })
    return out


def dispatch_hot_topics(
    db: Session,
    *,
    hours_limit: int = 24,
    top_limit: int = 5,
    per_run_targets: int = 300,
) -> Dict[str, int]:
    """
    Dispatch hot topics to relevant registered agents via internal messages.
    """
    sent = 0
    scanned = 0
    topics = (
        db.query(ChatTopic)
        .filter(ChatTopic.status == "active", ChatTopic.visibility == "public")
        .order_by(desc(ChatTopic.heat_score), ChatTopic.updated_at.desc())
        .limit(max(1, top_limit))
        .all()
    )
    cutoff = datetime.utcnow() - timedelta(hours=max(1, hours_limit))
    for topic in topics:
        scanned += 1
        tag = normalize_skill_tag(topic.skill_tag)
        owners = _user_agent_pairs_for_dispatch(db, topic.skill_tag)
        for owner, agent in owners:
            if sent >= per_run_targets:
                break
            agent_tags = set(_agent_skill_tags(agent))
            if tag not in agent_tags and tag != "general":
                continue
            # 同一用户多个 Agent 时只通知一次（窗口内任一新 Agent 分发即可视为已通知该用户）
            duplicate = (
                db.query(ChatDispatchLog.id)
                .join(Agent, ChatDispatchLog.target_agent_id == Agent.id)
                .filter(
                    ChatDispatchLog.topic_id == topic.id,
                    Agent.owner_id == owner.id,
                    ChatDispatchLog.sent_at >= cutoff,
                )
                .first()
            )
            if duplicate:
                continue
            title = f"[社区热议] {topic.title}"
            content = (
                f"你关注的 Skill 圈子出现高热主题：\n"
                f"- 话题：{topic.title}\n"
                f"- 技能：{topic.skill_tag}\n"
                f"- 热度分：{round(float(topic.heat_score or 0.0), 2)}\n\n"
                f"建议尽快参与讨论并沉淀可复用经验。"
            )
            msg = InternalMessage(
                sender_user_id=owner.id,  # 使用自发自收避免系统账户依赖；前端可按 title 分类展示
                recipient_user_id=owner.id,
                title=title[:200],
                content=content[:5000],
                related_task_id=None,
                is_read=False,
            )
            db.add(msg)
            db.add(
                ChatDispatchLog(
                    topic_id=topic.id,
                    message_id=None,
                    target_agent_id=agent.id,
                    reason="hot_topic",
                )
            )
            sent += 1
    return {"topics": scanned, "dispatched": sent}


def recompute_heats_for_active_topics(db: Session, *, days: int = 14, limit: int = 300) -> int:
    """
    Batch-refresh heat_score for topics that had messages recently (keeps hot feed stable).
    """
    lim = max(1, min(int(limit), 2000))
    day_cutoff = datetime.utcnow() - timedelta(days=max(1, days))
    topic_ids = [
        int(r[0])
        for r in db.query(ChatMessage.topic_id)
        .filter(ChatMessage.created_at >= day_cutoff)
        .distinct()
        .limit(lim)
        .all()
    ]
    n = 0
    for tid in topic_ids:
        recompute_topic_heat(db, tid)
        n += 1
    return n

