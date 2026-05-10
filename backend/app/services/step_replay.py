"""
Step-level execution replay.

Creates a ``ExecutionRun`` record per ``/tasks/{id}/execute`` call and
persists a sequence of ``ExecutionStep`` rows so operators / publishers
can inspect what happened on a failed or slow run.

The recorder is safe to use inside a normal FastAPI request session and
never raises out of its own bookkeeping path — if DB writes fail we
silently degrade rather than blocking the execution.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session


@dataclass
class RecordedStep:
    idx: int
    kind: str
    name: Optional[str]
    input: Optional[Dict[str, Any]] = None
    output: Optional[Dict[str, Any]] = None
    ok: bool = True
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration_ms: int = 0
    tokens: int = 0
    cost_credits: int = 0


class RunRecorder:
    """Collects steps for a single execution run.

    Use as::

        rec = RunRecorder(db, task_id=1, user_id=7)
        rec.start()
        rec.step("tool", name="search", input={"q": "x"}, output={...})
        rec.finish(ok=True, summary={...})
    """

    def __init__(self, db: Session, *, task_id: int, user_id: Optional[int] = None):
        self.db = db
        self.task_id = int(task_id)
        self.user_id = user_id
        self.run_id = uuid.uuid4().hex
        self._steps: List[RecordedStep] = []
        self._t0 = time.monotonic()
        self._run_row = None

    # ---------- lifecycle ----------

    def start(self, meta: Optional[Dict[str, Any]] = None) -> str:
        from app.database.relational_db import ExecutionRun

        try:
            run = ExecutionRun(
                run_id=self.run_id,
                task_id=self.task_id,
                started_at=datetime.utcnow(),
                ok=False,
                triggered_by_user_id=self.user_id,
            )
            self.db.add(run)
            self.db.flush()
            self._run_row = run
            self.step("start", name="run_start", input=meta or {})
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass
        return self.run_id

    def step(
        self,
        kind: str,
        *,
        name: Optional[str] = None,
        input: Optional[Dict[str, Any]] = None,
        output: Optional[Dict[str, Any]] = None,
        ok: bool = True,
        error: Optional[str] = None,
        duration_ms: int = 0,
        tokens: int = 0,
        cost_credits: int = 0,
    ) -> None:
        from app.database.relational_db import ExecutionStep

        idx = len(self._steps)
        rs = RecordedStep(
            idx=idx,
            kind=kind,
            name=name,
            input=input,
            output=output,
            ok=ok,
            error=error,
            duration_ms=int(duration_ms or 0),
            tokens=int(tokens or 0),
            cost_credits=int(cost_credits or 0),
        )
        self._steps.append(rs)
        try:
            row = ExecutionStep(
                run_id=self.run_id,
                task_id=self.task_id,
                idx=idx,
                kind=kind,
                name=(name or "")[:120] or None,
                input=_truncate_payload(input),
                output=_truncate_payload(output),
                ok=bool(ok),
                error=(error or None),
                duration_ms=int(duration_ms or 0),
                tokens=int(tokens or 0),
                cost_credits=int(cost_credits or 0),
            )
            self.db.add(row)
            self.db.flush()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    def finish(
        self,
        *,
        ok: bool,
        quota_exceeded: bool = False,
        error: Optional[str] = None,
        summary: Optional[Dict[str, Any]] = None,
        tokens_used: int = 0,
        cost_credits: int = 0,
    ) -> None:
        self.step(
            "end",
            name="run_end",
            output=summary or {},
            ok=bool(ok),
            error=error,
        )
        if not self._run_row:
            return
        try:
            self._run_row.ok = bool(ok)
            self._run_row.quota_exceeded = bool(quota_exceeded)
            self._run_row.error = (error or None)
            self._run_row.tokens_used = int(tokens_used or 0)
            self._run_row.cost_credits = int(cost_credits or 0)
            self._run_row.duration_ms = int((time.monotonic() - self._t0) * 1000)
            self._run_row.ended_at = datetime.utcnow()
            self.db.flush()
            self.db.commit()
        except Exception:
            try:
                self.db.rollback()
            except Exception:
                pass

    # ---------- read helpers ----------

    @property
    def steps(self) -> List[RecordedStep]:
        return list(self._steps)


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


_MAX_JSON_BYTES = 4096


def _truncate_payload(obj: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    try:
        import json

        raw = json.dumps(obj, ensure_ascii=False, default=str)
        if len(raw) <= _MAX_JSON_BYTES:
            return obj
        return {"_truncated": True, "_preview": raw[: _MAX_JSON_BYTES]}
    except Exception:
        return {"_invalid": True}


def serialize_step(s: Any) -> Dict[str, Any]:
    return {
        "idx": int(getattr(s, "idx", 0) or 0),
        "kind": getattr(s, "kind", None),
        "name": getattr(s, "name", None),
        "input": getattr(s, "input", None),
        "output": getattr(s, "output", None),
        "ok": bool(getattr(s, "ok", True)),
        "error": getattr(s, "error", None),
        "started_at": (
            getattr(s, "started_at", None).isoformat() + "Z"
            if getattr(s, "started_at", None)
            else None
        ),
        "duration_ms": int(getattr(s, "duration_ms", 0) or 0),
        "tokens": int(getattr(s, "tokens", 0) or 0),
        "cost_credits": int(getattr(s, "cost_credits", 0) or 0),
    }


def serialize_run(r: Any) -> Dict[str, Any]:
    return {
        "run_id": getattr(r, "run_id", None),
        "task_id": int(getattr(r, "task_id", 0) or 0),
        "ok": bool(getattr(r, "ok", False)),
        "quota_exceeded": bool(getattr(r, "quota_exceeded", False)),
        "error": getattr(r, "error", None),
        "tokens_used": int(getattr(r, "tokens_used", 0) or 0),
        "cost_credits": int(getattr(r, "cost_credits", 0) or 0),
        "duration_ms": int(getattr(r, "duration_ms", 0) or 0),
        "started_at": (
            getattr(r, "started_at", None).isoformat() + "Z"
            if getattr(r, "started_at", None)
            else None
        ),
        "ended_at": (
            getattr(r, "ended_at", None).isoformat() + "Z"
            if getattr(r, "ended_at", None)
            else None
        ),
    }
