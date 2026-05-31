@router.get("/agents/{agent_id}/skills")
def get_agent_skills(
    agent_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """技能维度 XP：公开可读（便于 Agent 主页展示）；折旧策略详情仅拥有者可见。"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    uid = None
    if current_user and current_user.get("user_id") is not None:
        try:
            uid = int(current_user["user_id"])
        except (TypeError, ValueError):
            uid = None
    is_owner = uid is not None and int(agent.owner_id) == uid
    tasks = db.query(Task).filter(Task.agent_id == agent_id, Task.status == "completed").all()
    xp_map = agent_skill_xp_map(db, agent_id)
    dec = skill_decay_meta(tasks)
    xp_map = apply_skill_decay(xp_map, float(dec.get("ratio") or 0.0))
    items = []
    for name, xp in sorted(xp_map.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = level_from_xp(int(xp))
        items.append({"name": name, "xp": int(xp), **lv})
    decay_out: Dict[str, Any] = {
        "ratio": float(dec.get("ratio") or 0.0),
        "last_active_at": iso_utc(dec.get("last_active_at")),
    }
    if is_owner:
        decay_out["policy"] = {
            "idle_days": SKILL_DECAY_IDLE_DAYS,
            "weekly_ratio": SKILL_DECAY_WEEKLY_RATIO,
            "max_ratio": SKILL_DECAY_MAX_RATIO,
        }
    return {
        "agent_id": agent_id,
        "items": items,
        "decay": decay_out,
        "viewer_is_owner": is_owner,
    }
