"""反向竞标（Reverse Auction）服务。

发布方在 `POST /tasks` 时可开启 `auction`，以 `max_reward` 为上限先从信用点中扣除（等同于 escrow）。
Agent 在窗口期内提交 `(price, eta_hours, proposal)`；发布方选标 → 任务定价按中标价重设，
多余的 `max_reward - price` 差额退还给发布方。

本模块不做数据库事务，所有状态修改由 caller 在同一事务中完成。
"""
from __future__ import annotations

import copy
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm.attributes import flag_modified

from app.database.relational_db import Task


AUCTION_STATUS_OPEN = "open"
AUCTION_STATUS_AWARDED = "awarded"
AUCTION_STATUS_CANCELLED = "cancelled"
AUCTION_STATUS_EXPIRED = "expired"


def _now() -> datetime:
    return datetime.utcnow()


def get_auction(task: Task) -> Optional[Dict[str, Any]]:
    d = task.input_data if isinstance(getattr(task, "input_data", None), dict) else {}
    a = d.get("auction") if isinstance(d, dict) else None
    if not isinstance(a, dict) or not a.get("enabled"):
        return None
    return a


def save_auction_to_task(task: Task, auction: Dict[str, Any]) -> None:
    base = copy.deepcopy(task.input_data) if isinstance(task.input_data, dict) else {}
    base["auction"] = copy.deepcopy(auction)
    task.input_data = base
    try:
        flag_modified(task, "input_data")
    except Exception:
        pass


def _parse_dt(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is not None:
                dt = dt.replace(tzinfo=None)
            return dt
        except ValueError:
            return None
    return None


def build_auction_plan(
    *,
    max_reward: int,
    min_reward: int = 0,
    deadline: Optional[str] = None,
    auto_pick: str = "manual",
) -> Dict[str, Any]:
    """发布阶段构造竞拍计划；保证 max >= min >= 0 并解析 deadline。"""
    if max_reward <= 0:
        raise ValueError("开启反向竞标须设置大于 0 的最高报价 max_reward")
    if min_reward < 0:
        raise ValueError("最低报价 min_reward 不能为负")
    if min_reward > max_reward:
        raise ValueError("min_reward 不能大于 max_reward")
    dl = _parse_dt(deadline)
    if deadline and dl is None:
        raise ValueError("deadline 格式无效，需为 ISO8601 时间字符串")
    if dl is not None and dl <= _now():
        raise ValueError("deadline 必须晚于当前时间")
    auto = (auto_pick or "manual").strip().lower()
    if auto not in ("manual", "lowest_price"):
        raise ValueError("auto_pick 仅支持 manual 或 lowest_price")
    return {
        "enabled": True,
        "status": AUCTION_STATUS_OPEN,
        "min_reward": int(min_reward),
        "max_reward": int(max_reward),
        "deadline": dl.isoformat() + "Z" if dl else None,
        "auto_pick": auto,
        "selected_bid_id": None,
        "awarded_at": None,
        "bid_count": 0,
    }


def is_auction_open(auction: Dict[str, Any]) -> bool:
    if not auction or auction.get("status") != AUCTION_STATUS_OPEN:
        return False
    dl = _parse_dt(auction.get("deadline"))
    if dl is not None and dl <= _now():
        return False
    return True


def validate_bid_price(auction: Dict[str, Any], price: int) -> None:
    if price <= 0:
        raise ValueError("报价必须大于 0")
    mn = int(auction.get("min_reward", 0) or 0)
    mx = int(auction.get("max_reward", 0) or 0)
    if mx > 0 and price > mx:
        raise ValueError(f"报价不能高于上限 {mx}")
    if mn > 0 and price < mn:
        raise ValueError(f"报价不能低于底价 {mn}")


def mark_auction_awarded(auction: Dict[str, Any], *, selected_bid_id: int) -> Dict[str, Any]:
    auction = dict(auction)
    auction["status"] = AUCTION_STATUS_AWARDED
    auction["selected_bid_id"] = int(selected_bid_id)
    auction["awarded_at"] = _now().isoformat() + "Z"
    return auction


def mark_auction_cancelled(auction: Dict[str, Any]) -> Dict[str, Any]:
    auction = dict(auction)
    auction["status"] = AUCTION_STATUS_CANCELLED
    return auction


def serialize_bid(b: Any, *, hide_proposal: bool = False) -> Dict[str, Any]:
    """将 TaskBid ORM 对象转换为 API 响应结构。"""
    return {
        "id": b.id,
        "task_id": b.task_id,
        "agent_id": b.agent_id,
        "bidder_user_id": b.bidder_user_id,
        "price": int(b.price or 0),
        "eta_hours": int(b.eta_hours) if b.eta_hours is not None else None,
        "proposal": None if hide_proposal else (b.proposal or ""),
        "status": b.status or "active",
        "created_at": b.created_at.isoformat() + "Z" if b.created_at else None,
        "updated_at": b.updated_at.isoformat() + "Z" if b.updated_at else None,
    }


def pick_lowest_price(bids: List[Any]) -> Optional[Any]:
    """在 active 出价中按价格升序、创建时间升序选一条。"""
    active = [b for b in bids if (b.status or "active") == "active"]
    if not active:
        return None
    return sorted(active, key=lambda b: (int(b.price or 10 ** 9), b.created_at or datetime.max))[0]
