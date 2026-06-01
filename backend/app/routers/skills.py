"""Skill marketplace, agent templates, scenario packs."""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.relational_db import (
    Agent, PublishedAgentTemplate, PublishedSkill, SystemLog, Task, User, get_db,
)
from app.domain.skill_xp import task_related_skill
from app.domain.task_helpers import task_extra as _task_extra
from app.security import get_current_user
from app.services.preflight import enforce_preflight
from app.services.skill_contract import validate_contract, validate_payload
from app.utils.datetime_iso import iso_utc

router = APIRouter(tags=["Skills · Skill 市场"])

def _count_completed_tasks_for_agent(db: Session, agent_id: int) -> int:
    return db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").count()


def _get_agent_ids_by_skill_token(db: Session, uid: Optional[int] = None, skill_token: str = "") -> List[int]:
    """根据 config.skill_bound_token 找到对应 Agent id。

    注：为兼容不同数据库 JSON 查询能力，这里使用 Python 方式筛选。
    """
    if not skill_token:
        return []
    q = db.query(Agent)
    if uid is not None:
        q = q.filter(Agent.owner_id == uid)
    agents = q.all()
    out: List[int] = []
    for a in agents:
        cfg = a.config or {}
        if cfg.get("skill_bound_token") == skill_token:
            out.append(a.id)
    return out


def _count_completed_tasks_for_skill_token(db: Session, skill_token: str) -> int:
    agent_ids = _get_agent_ids_by_skill_token(db, None, skill_token)
    if not agent_ids:
        return 0
    return db.query(Task).filter(Task.agent_id.in_(agent_ids), Task.status == "completed").count()
class PublishSkillBody(BaseModel):
    """通过 Skill 发布到平台：生成/更新技能市场条目。"""
    # NOTE: translated comment in English.
    # NOTE: translated comment in English.
    skill_token: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    version_tag: Optional[str] = "v1"
    download_skill_url: Optional[str] = None
    contract_schema: Optional[dict] = None
    failure_semantics: Optional[dict] = None
    idempotency_hint: Optional[str] = None


class GithubSkillSyncBody(BaseModel):
    top_n: int = 20
    min_stars: int = 30
    query: Optional[str] = None
    force_update: bool = False


class SkillContractValidateBody(BaseModel):
    contract_schema: dict
    failure_semantics: Optional[dict] = None
    sample_payload: Optional[dict] = None


class WorkflowPlanBody(BaseModel):
    nodes: List[int]
    edges: List[dict] = []


class CircuitBreakerControlBody(BaseModel):
    host: str
    action: str  # reset | open | half_open | close
def _publisher_for_skill_token(db: Session, skill_token: str) -> tuple:
    """返回 (publisher_username, publisher_user_id)。"""
    agents = db.query(Agent).all()
    for a in agents:
        cfg = a.config or {}
        if (cfg.get("skill_bound_token") or "").strip() == skill_token:
            u = db.query(User).filter(User.id == a.owner_id).first()
            return (u.username if u else "", a.owner_id)
    return ("", None)


def _agent_id_for_skill_token(db: Session, skill_token: str) -> Optional[int]:
    tok = (skill_token or "").strip()
    if not tok:
        return None
    for a in db.query(Agent).all():
        cfg = a.config or {}
        if (cfg.get("skill_bound_token") or "").strip() == tok:
            return int(a.id)
    return None


async def _fetch_github_hot_skill_repos(top_n: int, min_stars: int, query: Optional[str]) -> List[dict]:
    q = (query or "").strip() or "skill (openclaw OR mcp OR agent OR cursor) in:name,description,topics"
    q = f"{q} stars:>={max(0, int(min_stars))}"
    url = "https://api.github.com/search/repositories"
    params = {
        "q": q,
        "sort": "stars",
        "order": "desc",
        "per_page": max(1, min(int(top_n), 50)),
        "page": 1,
    }
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(url, params=params, headers=headers)
        if resp.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"github api error: {resp.status_code}")
        data = resp.json()
    repos = data.get("items") or []
    out: List[dict] = []
    for r in repos:
        full_name = str(r.get("full_name") or "").strip()
        html_url = str(r.get("html_url") or "").strip()
        if not full_name or not html_url:
            continue
        owner = str((r.get("owner") or {}).get("login") or "").strip()
        repo = str(r.get("name") or "").strip()
        archive_url = f"https://github.com/{full_name}/archive/refs/heads/{str(r.get('default_branch') or 'main')}.zip"
        stars = int(r.get("stargazers_count") or 0)
        desc = (str(r.get("description") or "").strip() or "GitHub 热门 Skill 仓库")
        topics = [str(x).strip() for x in (r.get("topics") or []) if str(x).strip()]
        out.append({
            "full_name": full_name,
            "name": repo or full_name.split("/")[-1],
            "owner": owner,
            "html_url": html_url,
            "archive_url": archive_url,
            "stars": stars,
            "description": desc,
            "topics": topics[:10],
        })
    return out
@router.get("/agent-templates")
def get_agent_templates(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    verified_only: bool = False,
    agent_type: Optional[str] = None,
    sort: str = "created_desc",  # created_desc | tasks_desc
):
    """Agent 模板 / Skill 市场：可下载的 Agent 模板与 Skill 列表（含平台 verify、完成任务数）。"""
    q = db.query(PublishedAgentTemplate).join(Agent)
    if verified_only:
        q = q.filter(PublishedAgentTemplate.verified.is_(True))
    if agent_type and agent_type.strip():
        q = q.filter(Agent.agent_type == agent_type.strip())
    if sort == "tasks_desc":
        rows = q.all()
        scored = [(t, _count_completed_tasks_for_agent(db, t.agent_id)) for t in rows]
        scored.sort(key=lambda x: (-x[1], -x[0].id))
        rows = [x[0] for x in scored]
    else:
        rows = q.order_by(PublishedAgentTemplate.created_at.desc()).all()
    total = len(rows)
    rows = rows[skip : skip + limit]
    items = []
    from app.services.reputation import compute_agent_reputation

    for t in rows:
        tasks_completed = _count_completed_tasks_for_agent(db, t.agent_id)
        owner = db.query(User).filter(User.id == t.agent.owner_id).first() if t.agent else None
        rep = compute_agent_reputation(db, t.agent_id) or {}
        items.append({
            "id": t.id,
            "name": t.name,
            "description": t.description or "",
            "verified": t.verified,
            "version_tag": t.version_tag or "v1",
            "tasks_completed": tasks_completed,
            "agent_id": t.agent_id,
            "reputation_score": int(rep.get("reputation_score", 0) or 0),
            "agent_type": t.agent.agent_type if t.agent else None,
            "publisher_username": owner.username if owner else "",
            "publisher_user_id": t.agent.owner_id if t.agent else None,
            "download_agent_url": t.download_agent_url,
            "download_skill_url": t.download_skill_url,
            "created_at": iso_utc(t.created_at) if getattr(t, "created_at", None) else None,
        })
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/agent-templates/stats")
def get_agent_templates_stats(db: Session = Depends(get_db)):
    """Agent 模板市场统计：模板数、已验证数、累计完成任务数。"""
    template_count = db.query(PublishedAgentTemplate).count()
    verified_count = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.verified.is_(True)).count()
    tasks_completed = db.query(Task).filter(Task.status == "completed").count()
    return {
        "template_count": template_count,
        "verified_count": verified_count,
        "tasks_completed": tasks_completed,
    }


class PublishAgentTemplateBody(BaseModel):
    """发布 Agent 为市场模板"""
    agent_id: int
    name: str
    description: str = ""
    version_tag: str = "v1"
    download_agent_url: Optional[str] = None
    download_skill_url: Optional[str] = None


@router.post("/agent-templates")
def publish_agent_template(
    body: PublishAgentTemplateBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """将本人名下、至少完成过 1 个任务的 Agent 发布为市场模板（一 Agent 仅可发布一条）。"""
    uid = int(current_user["user_id"])
    agent = db.query(Agent).filter(Agent.id == body.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    if agent.owner_id != uid:
        raise HTTPException(status_code=403, detail="Only the owner can publish this agent")
    completed = _count_completed_tasks_for_agent(db, agent.id)
    if completed < 1:
        raise HTTPException(status_code=400, detail="Agent must have at least one completed task to publish")
    existing = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.agent_id == agent.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="This agent is already published as a template")
    name = (body.name or agent.name or "").strip() or agent.name
    version_tag = ((body.version_tag or "v1").strip() or "v1")[:64]
    template = PublishedAgentTemplate(
        agent_id=agent.id,
        name=name,
        description=(body.description or "").strip() or None,
        version_tag=version_tag,
        download_agent_url=(body.download_agent_url or "").strip() or None,
        download_skill_url=(body.download_skill_url or "").strip() or None,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    tasks_completed = _count_completed_tasks_for_agent(db, agent.id)
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description or "",
        "verified": template.verified,
        "version_tag": template.version_tag or "v1",
        "tasks_completed": tasks_completed,
        "agent_type": agent.agent_type,
        "download_agent_url": template.download_agent_url,
        "download_skill_url": template.download_skill_url,
    }

@router.delete("/agent-templates/{template_id}")
def delete_agent_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    tpl = db.query(PublishedAgentTemplate).filter(PublishedAgentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    owner_id = tpl.agent.owner_id if tpl.agent else None
    if owner_id != uid and not (me and bool(getattr(me, "is_superuser", False))):
        raise HTTPException(status_code=403, detail="Only publisher/admin can delete template")
    db.delete(tpl)
    db.commit()
    return {"ok": True, "id": template_id}
@router.get("/skills/packs")
def get_skill_scenario_packs(
    scenario: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """场景 Skill 包：面向 Agent 开发者的精选能力组合与 OpenClaw 安装提示。"""
    from app.services.skill_packs import count_open_tasks_for_pack, list_scenario_packs

    packs = list_scenario_packs(scenario=scenario)
    token_set = set()
    for p in packs:
        for tok in p.get("skill_tokens") or []:
            if tok:
                token_set.add(str(tok).strip())
    skill_by_token: Dict[str, Any] = {}
    if token_set:
        rows = db.query(PublishedSkill).filter(PublishedSkill.skill_token.in_(list(token_set))).all()
        for s in rows:
            skill_by_token[s.skill_token] = {
                "id": s.id,
                "name": s.name,
                "verified": bool(s.verified),
                "download_skill_url": s.download_skill_url,
            }
    app_base = os.getenv("CLAWJOB_APP_URL", "https://app.clawjob.com.cn").rstrip("/")
    api_base = os.getenv("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
    out = []
    for p in packs:
        item = dict(p)
        resolved = []
        for tok in item.get("skill_tokens") or []:
            if tok in skill_by_token:
                resolved.append(skill_by_token[tok])
        item["resolved_skills"] = resolved
        item["install_copy"] = (
            f"# {item.get('title_zh')}\n"
            f"{item.get('openclaw_install', '')}\n"
            f"# Docs: {app_base}/skill.md | API: {api_base}"
        )
        open_n = count_open_tasks_for_pack(db, item)
        item["open_tasks_count"] = open_n
        item["recommended_tasks_url"] = f"{api_base}/skills/packs/{item.get('id')}/recommended-tasks"
        out.append(item)
    return {"items": out, "total": len(out), "skill_doc_url": f"{app_base}/skill.md"}


@router.get("/skills/packs/{pack_id}/recommended-tasks")
def get_skill_pack_recommended_tasks(
    pack_id: str,
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """返回与场景包 category 匹配的开放任务（供 Agent 接取）。"""
    from app.services.skill_packs import list_scenario_packs, recommended_tasks_for_pack

    if not any(p.get("id") == pack_id for p in list_scenario_packs()):
        raise HTTPException(status_code=404, detail="场景包不存在")
    limit = max(1, min(int(limit or 10), 30))
    tasks = recommended_tasks_for_pack(db, pack_id, limit=limit)
    return {
        "pack_id": pack_id,
        "tasks": tasks,
        "total": len(tasks),
    }
@router.get("/skills")
def get_skills(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    verified_only: bool = False,
    sort: str = "created_desc",
):
    """Skill 市场：列出已发布 Skill，并给出完成任务数（用于 verify 展示）。"""
    q = db.query(PublishedSkill)
    if verified_only:
        q = q.filter(PublishedSkill.verified.is_(True))
    if sort == "tasks_desc":
        rows = q.all()
        scored = [(s, _count_completed_tasks_for_skill_token(db, s.skill_token)) for s in rows]
        scored.sort(key=lambda x: (-x[1], -x[0].id))
        rows = [x[0] for x in scored]
    else:
        rows = q.order_by(PublishedSkill.created_at.desc()).all()
    total = len(rows)
    rows = rows[skip : skip + limit]
    out = []
    from app.services.reputation import compute_agent_reputation

    for s in rows:
        tasks_completed = _count_completed_tasks_for_skill_token(db, s.skill_token)
        pub_name, pub_uid = _publisher_for_skill_token(db, s.skill_token)
        agent_id = _agent_id_for_skill_token(db, s.skill_token)
        rep_score = 0
        if agent_id:
            rep = compute_agent_reputation(db, agent_id) or {}
            rep_score = int(rep.get("reputation_score", 0) or 0)
        out.append({
            "id": s.id,
            "skill_token": s.skill_token,
            "name": s.name,
            "description": s.description or "",
            "verified": bool(s.verified),
            "version_tag": s.version_tag or "v1",
            "tasks_completed": int(tasks_completed),
            "agent_id": agent_id,
            "reputation_score": rep_score,
            "download_skill_url": s.download_skill_url,
            "publisher_username": pub_name,
            "publisher_user_id": pub_uid,
            "pricing_model": s.pricing_model or "free",
            "price_per_unit": int(s.price_per_unit or 0),
            "revenue_share_bp": int(s.revenue_share_bp or 7000),
            "author_user_id": s.author_user_id,
            "created_at": iso_utc(s.created_at) if getattr(s, "created_at", None) else None,
        })
    return {"items": out, "total": total, "skip": skip, "limit": limit}


@router.get("/skills/stats")
def get_skills_stats(db: Session = Depends(get_db)):
    """Skill 市场统计：模板数、已验证数、累计完成任务数（基于 token 推导）。"""
    skills = db.query(PublishedSkill).all()
    skill_count = len(skills)
    verified_count = sum(1 for s in skills if bool(s.verified))
    tasks_completed_total = 0
    for s in skills:
        tasks_completed_total += _count_completed_tasks_for_skill_token(db, s.skill_token)
    return {
        "skill_count": skill_count,
        "verified_count": verified_count,
        "tasks_completed": tasks_completed_total,
    }


@router.get("/skills/{skill_id}/tasks")
def get_skill_related_tasks(
    skill_id: int,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 30,
):
    row = db.query(PublishedSkill).filter(PublishedSkill.id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Skill not found")
    token = (row.skill_token or "").strip()
    if not token:
        return {"items": [], "total": 0, "skill_id": skill_id, "skill_token": ""}
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    matched = []
    for t in tasks:
        rel = task_related_skill(db, t)
        if rel and (rel.get("skill_token") or "") == token:
            owner = db.query(User).filter(User.id == t.owner_id).first()
            matched.append({
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "owner_id": t.owner_id,
                "publisher_name": owner.username if owner else "",
                "agent_id": t.agent_id,
                "created_at": iso_utc(t.created_at),
                **_task_extra(t, db),
            })
    total = len(matched)
    items = matched[skip : skip + limit]
    return {"items": items, "total": total, "skill_id": skill_id, "skill_token": token}


@router.post("/skills/contract/validate")
def validate_skill_contract(
    body: SkillContractValidateBody,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    ok, errors = validate_contract(body.contract_schema, body.failure_semantics)
    payload_ok = True
    payload_errors: List[str] = []
    if ok and body.sample_payload is not None:
        payload_ok, payload_errors = validate_payload(body.contract_schema, body.sample_payload)
    return {
        "ok": bool(ok and payload_ok),
        "contract_ok": ok,
        "contract_errors": errors,
        "payload_ok": payload_ok,
        "payload_errors": payload_errors,
    }


@router.post("/skills/publish")
def publish_skill(
    body: PublishSkillBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Skill 分享：让具备 Skill 的 OpenClaw 直接发布自己的 Skill 到平台。

    验证逻辑（简化）：
    - 必须能在当前用户名下找到至少一个 Agent，其 config.skill_bound_token 与 skill_token 对齐；
    - verified 默认为根据任务完成数推导：tasks_completed > 0 => True，否则 False。
    """
    preflight = enforce_preflight("skill_publish")
    uid = int(current_user["user_id"])
    contract_profile = None
    if body.contract_schema is not None:
        c_ok, c_errs = validate_contract(body.contract_schema, body.failure_semantics)
        if not c_ok:
            raise HTTPException(status_code=400, detail={"message": "Invalid skill contract", "errors": c_errs})
        contract_profile = {
            "schema_version": ((body.contract_schema or {}).get("$schema") or "custom"),
            "idempotency_hint": ((body.idempotency_hint or "").strip() or "none")[:128],
            "failure_codes": len(((body.failure_semantics or {}).get("codes") or []) if isinstance(body.failure_semantics, dict) else []),
        }
    skill_token = (body.skill_token or "").strip() if body.skill_token else ""

    # NOTE: translated comment in English.
    if not skill_token:
        tokens = set()
        my_agents = db.query(Agent).filter(Agent.owner_id == uid).all()
        for a in my_agents:
            cfg = a.config or {}
            tok = (cfg.get("skill_bound_token") or "").strip() if cfg else ""
            if tok:
                tokens.add(tok)
        tokens_list = sorted(list(tokens))
        if len(tokens_list) == 1:
            skill_token = tokens_list[0]
        elif len(tokens_list) == 0:
            raise HTTPException(status_code=400, detail="skill_token 未提供，且当前用户下没有可用的 skill_bound_token")
        else:
            raise HTTPException(status_code=400, detail="skill_token 未提供，当前用户下存在多个 skill_bound_token，请显式传入 skill_token")

    # NOTE: translated comment in English.
    agent_ids = _get_agent_ids_by_skill_token(db, uid=uid, skill_token=skill_token)
    if not agent_ids:
        raise HTTPException(status_code=403, detail="当前用户下未找到与该 skill_token 对齐的 Agent（请在注册 Agent 时设置 skill_bound_token）")

    tasks_completed = _count_completed_tasks_for_skill_token(db, skill_token)
    verified = tasks_completed > 0

    name = (body.name or "").strip() or f"Skill {skill_token[:8]}"
    description = (body.description or "").strip() if body.description else None
    version_tag = ((body.version_tag or "v1").strip() if body.version_tag else "v1")[:64] or "v1"
    download_skill_url = (body.download_skill_url or "").strip() if body.download_skill_url else None

    existing = db.query(PublishedSkill).filter(PublishedSkill.skill_token == skill_token).first()
    if existing:
        existing.name = name
        existing.description = description
        existing.download_skill_url = download_skill_url
        existing.version_tag = version_tag
        existing.verified = bool(verified)
        db.commit()
        db.refresh(existing)
        skill_id = existing.id
    else:
        row = PublishedSkill(
            skill_token=skill_token,
            name=name,
            description=description,
            verified=bool(verified),
            version_tag=version_tag,
            download_skill_url=download_skill_url,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        skill_id = row.id
    if contract_profile is not None:
        try:
            db.add(SystemLog(
                level="info",
                category="skill_contract",
                message="skill_contract_validated",
                user_id=uid,
                extra={"skill_token": skill_token, **contract_profile},
            ))
            db.commit()
        except Exception:
            db.rollback()

    return {
        "id": skill_id,
        "skill_token": skill_token,
        "name": name,
        "description": description or "",
        "verified": bool(verified),
        "version_tag": version_tag,
        "tasks_completed": int(tasks_completed),
        "download_skill_url": download_skill_url,
        "preflight": preflight,
        "contract_profile": contract_profile,
    }


@router.post("/skills/sync/github-hot")
async def sync_skills_from_github_hot(
    body: GithubSkillSyncBody,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """同步 GitHub 热门 Skill 仓库到平台 Skill 市场（含链接与描述）。"""
    _ = current_user
    import app.main as _app_main  # tests monkeypatch app.main._fetch_github_hot_skill_repos

    repos = await _app_main._fetch_github_hot_skill_repos(body.top_n, body.min_stars, body.query)
    created = 0
    updated = 0
    items: List[dict] = []
    for r in repos:
        skill_token = f"gh::{r['full_name']}".lower()[:256]
        name = f"{r['name']} (GitHub)"
        topics_txt = ", ".join(r.get("topics") or [])
        desc = (
            f"{r['description']}\n\n"
            f"GitHub: {r['html_url']}\n"
            f"Stars: {r['stars']}\n"
            f"Topics: {topics_txt if topics_txt else '-'}"
        )[:2000]
        row = db.query(PublishedSkill).filter(PublishedSkill.skill_token == skill_token).first()
        if row:
            if body.force_update:
                row.name = name[:256]
                row.description = desc
                row.download_skill_url = r["archive_url"][:2000]
                row.verified = bool(r["stars"] >= max(100, body.min_stars))
                row.version_tag = "github-hot"
                updated += 1
        else:
            row = PublishedSkill(
                skill_token=skill_token,
                name=name[:256],
                description=desc,
                verified=bool(r["stars"] >= max(100, body.min_stars)),
                version_tag="github-hot",
                download_skill_url=r["archive_url"][:2000],
            )
            db.add(row)
            created += 1
        items.append({
            "skill_token": skill_token,
            "name": name,
            "github_url": r["html_url"],
            "download_skill_url": r["archive_url"],
            "description": r["description"],
            "stars": r["stars"],
        })
    db.commit()
    return {"ok": True, "created": created, "updated": updated, "total": len(items), "items": items}


@router.delete("/skills/{skill_id}")
def delete_skill_publish(
    skill_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    uid = int(current_user["user_id"])
    me = db.query(User).filter(User.id == uid).first()
    row = db.query(PublishedSkill).filter(PublishedSkill.id == skill_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Skill publish not found")
    owns_token = bool(_get_agent_ids_by_skill_token(db, uid=uid, skill_token=row.skill_token))
    if (not owns_token) and not (me and bool(getattr(me, "is_superuser", False))):
        raise HTTPException(status_code=403, detail="Only publisher/admin can delete skill publish")
    db.delete(row)
    db.commit()
    return {"ok": True, "id": skill_id}
