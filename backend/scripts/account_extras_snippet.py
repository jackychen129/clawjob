@router.get("/account/skill-tree")
def get_my_skill_tree(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    uid = int(current_user["user_id"])
    my_agents = db.query(Agent).filter(Agent.owner_id == uid).all()
    total: dict = {}
    max_decay = 0.0
    latest_active: Optional[datetime] = None
    for a in my_agents:
        tasks = db.query(Task).filter(Task.agent_id == a.id, Task.status == "completed").all()
        xp_map = agent_skill_xp_map(db, a.id)
        dec = skill_decay_meta(tasks)
        ratio = float(dec.get("ratio") or 0.0)
        xp_map = apply_skill_decay(xp_map, ratio)
        if ratio > max_decay:
            max_decay = ratio
        la = dec.get("last_active_at")
        if la and (latest_active is None or la > latest_active):
            latest_active = la
        for k, v in xp_map.items():
            total[k] = int(total.get(k, 0) or 0) + int(v or 0)
    nodes = []
    for name, xp in sorted(total.items(), key=lambda kv: (-kv[1], kv[0])):
        lv = level_from_xp(int(xp))
        nodes.append({"name": name, "xp": int(xp), **lv})
    return {
        "nodes": nodes[:24],
        "total_skills": len(nodes),
        "decay": {
            "max_ratio": float(round(max_decay, 4)),
            "last_active_at": iso_utc(latest_active),
            "policy": {
                "idle_days": SKILL_DECAY_IDLE_DAYS,
                "weekly_ratio": SKILL_DECAY_WEEKLY_RATIO,
                "max_ratio": SKILL_DECAY_MAX_RATIO,
            },
        },
    }
@router.get("/account/insights")
def my_insights(
    days: int = 90,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """登录用户自己的发布方报表。"""
    uid = int(current_user["user_id"])
    return _insights.publisher_report(db, user_id=uid, days=int(days or 90))
