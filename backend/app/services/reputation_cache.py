"""Redis-backed reputation card cache (10k agent scale)."""
from __future__ import annotations

from typing import Any, Dict, Optional


def _rep_key(agent_id: int) -> str:
    return f"clawjob:rep:agent:{int(agent_id)}"


def get_cached_reputation(agent_id: int) -> Optional[Dict[str, Any]]:
    try:
        from app.database.cache_db import get_redis_cache

        val = get_redis_cache().get_value(_rep_key(agent_id))
        return val if isinstance(val, dict) else None
    except Exception:
        return None


def set_cached_reputation(agent_id: int, card: Dict[str, Any], ttl: int = 300) -> None:
    try:
        from app.database.cache_db import get_redis_cache

        get_redis_cache().set_value(_rep_key(agent_id), card, expire=ttl)
    except Exception:
        pass


def invalidate_agent_reputation(agent_id: Optional[int]) -> None:
    if not agent_id:
        return
    try:
        from app.database.cache_db import get_redis_cache

        get_redis_cache().delete_key(_rep_key(int(agent_id)))
    except Exception:
        pass


def invalidate_agents_reputation(agent_ids: list) -> None:
    for aid in agent_ids:
        invalidate_agent_reputation(aid)
