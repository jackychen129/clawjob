"""
后台定时任务：社区话题热度批量刷新 + 热议站内信分发。

由 main.py lifespan 启动；可通过环境变量关闭或调整间隔。
"""
from __future__ import annotations

import asyncio
import logging
import os

logger = logging.getLogger("uvicorn.error")


def run_community_tick() -> None:
    """同步执行一轮维护（在线程池中调用，避免阻塞事件循环）。"""
    if os.getenv("CLAWJOB_COMMUNITY_BACKGROUND_JOBS", "1").strip() == "0":
        return
    if os.getenv("CLAWJOB_COMMUNITY_ENABLED", "1").strip() == "0":
        return

    from app.database.relational_db import SessionLocal
    from app.services import community as _community

    db = SessionLocal()
    heat_n = 0
    try:
        heat_limit = int(os.getenv("CLAWJOB_COMMUNITY_HEAT_BATCH_LIMIT", "300"))
        heat_n = _community.recompute_heats_for_active_topics(db, limit=max(1, heat_limit))
        db.commit()
    except Exception:
        logger.exception("community_tick heat recompute failed")
        db.rollback()
    finally:
        db.close()

    hot_enabled = os.getenv("CLAWJOB_COMMUNITY_HOT_DISPATCH_ENABLED", "1").strip() != "0"
    if not hot_enabled:
        logger.info("community_tick heat_rows=%s dispatch=skipped (hot disabled)", heat_n)
        return

    db = SessionLocal()
    try:
        top = int(os.getenv("CLAWJOB_COMMUNITY_DISPATCH_TOP_LIMIT", "5"))
        top = max(1, min(top, 20))
        cap = int(os.getenv("CLAWJOB_COMMUNITY_DISPATCH_MAX_TARGETS", "300"))
        disp = _community.dispatch_hot_topics(db, top_limit=top, per_run_targets=max(1, cap))
        db.commit()
        logger.info("community_tick heat_rows=%s dispatch=%s", heat_n, disp)
    except Exception:
        logger.exception("community_tick dispatch failed")
        db.rollback()
    finally:
        db.close()


async def run_community_background_loop(stop: asyncio.Event) -> None:
    interval = int(os.getenv("CLAWJOB_COMMUNITY_DISPATCH_INTERVAL_SEC", "900"))
    interval = max(60, interval)
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
            return
        except asyncio.TimeoutError:
            await asyncio.to_thread(run_community_tick)
