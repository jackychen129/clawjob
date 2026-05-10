"""
Execution sandbox quota helpers.

Enforces ``max_duration_seconds``, ``max_tokens``, and ``max_cost_credits`` on
task executions. The current implementation does not spawn a new subprocess
or container; instead it:
  - limits wall clock time with ``asyncio.wait_for``
  - exposes a ``QuotaMeter`` that callers increment; ``check()`` raises
    ``QuotaExceeded`` when any cap is crossed
  - returns a structured ``SandboxOutcome`` that the caller persists.

This gives us a uniform envelope and preserves the existing task_system
implementation while unblocking observability + cost-capping for Phase C.
"""
from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional


class QuotaExceeded(RuntimeError):
    def __init__(self, reason: str, detail: Optional[Dict[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail or {}


@dataclass
class ExecutionQuota:
    max_duration_seconds: int = 60
    max_tokens: int = 0  # 0 = unlimited
    max_cost_credits: int = 0  # 0 = unlimited

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "ExecutionQuota":
        d = data or {}
        def _i(k: str, default: int) -> int:
            try:
                v = int(d.get(k, default))
            except Exception:
                return default
            return max(0, v)
        return cls(
            max_duration_seconds=_i("max_duration_seconds", 60) or 60,
            max_tokens=_i("max_tokens", 0),
            max_cost_credits=_i("max_cost_credits", 0),
        )

    @classmethod
    def from_env(cls) -> "ExecutionQuota":
        def _e(k: str, default: int) -> int:
            try:
                return max(0, int(os.getenv(k, str(default))))
            except Exception:
                return default
        return cls(
            max_duration_seconds=_e("EXEC_MAX_DURATION", 60) or 60,
            max_tokens=_e("EXEC_MAX_TOKENS", 0),
            max_cost_credits=_e("EXEC_MAX_COST_CREDITS", 0),
        )

    def merge(self, other: Optional["ExecutionQuota"]) -> "ExecutionQuota":
        if not other:
            return self
        return ExecutionQuota(
            max_duration_seconds=other.max_duration_seconds or self.max_duration_seconds,
            max_tokens=other.max_tokens or self.max_tokens,
            max_cost_credits=other.max_cost_credits or self.max_cost_credits,
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "max_duration_seconds": self.max_duration_seconds,
            "max_tokens": self.max_tokens,
            "max_cost_credits": self.max_cost_credits,
        }


@dataclass
class QuotaMeter:
    quota: ExecutionQuota
    tokens_used: int = 0
    cost_credits: int = 0
    started_at: float = field(default_factory=time.monotonic)

    def check(self) -> None:
        now = time.monotonic()
        if self.quota.max_duration_seconds and (now - self.started_at) > self.quota.max_duration_seconds:
            raise QuotaExceeded(
                "duration_exceeded",
                {"limit": self.quota.max_duration_seconds, "elapsed": now - self.started_at},
            )
        if self.quota.max_tokens and self.tokens_used > self.quota.max_tokens:
            raise QuotaExceeded(
                "tokens_exceeded",
                {"limit": self.quota.max_tokens, "used": self.tokens_used},
            )
        if self.quota.max_cost_credits and self.cost_credits > self.quota.max_cost_credits:
            raise QuotaExceeded(
                "cost_exceeded",
                {"limit": self.quota.max_cost_credits, "used": self.cost_credits},
            )

    def add_tokens(self, n: int) -> None:
        if n > 0:
            self.tokens_used += int(n)
            self.check()

    def add_cost(self, n: int) -> None:
        if n > 0:
            self.cost_credits += int(n)
            self.check()

    def snapshot(self) -> Dict[str, Any]:
        return {
            "tokens_used": int(self.tokens_used),
            "cost_credits": int(self.cost_credits),
            "duration_ms": int((time.monotonic() - self.started_at) * 1000),
        }


@dataclass
class SandboxOutcome:
    ok: bool
    quota_exceeded: bool
    reason: Optional[str]
    duration_ms: int
    tokens_used: int
    cost_credits: int
    result: Any = None
    error: Optional[str] = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "quota_exceeded": self.quota_exceeded,
            "reason": self.reason,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cost_credits": self.cost_credits,
            "error": self.error,
        }


async def run_with_quota(
    func: Callable[[QuotaMeter], Awaitable[Any]],
    quota: ExecutionQuota,
) -> SandboxOutcome:
    """Run ``func(meter)`` inside a wall-clock budget.

    ``func`` receives a live ``QuotaMeter`` so it can report tokens / cost
    and trigger early termination via ``meter.check()``. On timeout or
    ``QuotaExceeded`` the outcome is marked ``quota_exceeded=True``.
    """
    meter = QuotaMeter(quota=quota)
    start = time.monotonic()
    try:
        timeout = quota.max_duration_seconds or None
        coro = func(meter)
        if timeout:
            result = await asyncio.wait_for(coro, timeout=timeout)
        else:
            result = await coro
        snap = meter.snapshot()
        return SandboxOutcome(
            ok=True,
            quota_exceeded=False,
            reason=None,
            duration_ms=snap["duration_ms"],
            tokens_used=snap["tokens_used"],
            cost_credits=snap["cost_credits"],
            result=result,
        )
    except asyncio.TimeoutError:
        snap = meter.snapshot()
        return SandboxOutcome(
            ok=False,
            quota_exceeded=True,
            reason="duration_exceeded",
            duration_ms=snap["duration_ms"],
            tokens_used=snap["tokens_used"],
            cost_credits=snap["cost_credits"],
            error=f"duration_exceeded>{quota.max_duration_seconds}s",
        )
    except QuotaExceeded as qe:
        snap = meter.snapshot()
        return SandboxOutcome(
            ok=False,
            quota_exceeded=True,
            reason=qe.reason,
            duration_ms=snap["duration_ms"],
            tokens_used=snap["tokens_used"],
            cost_credits=snap["cost_credits"],
            error=str(qe),
        )
    except Exception as e:
        elapsed = int((time.monotonic() - start) * 1000)
        return SandboxOutcome(
            ok=False,
            quota_exceeded=False,
            reason=None,
            duration_ms=elapsed,
            tokens_used=meter.tokens_used,
            cost_credits=meter.cost_credits,
            error=str(e)[:300],
        )
