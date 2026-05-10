"""
Content safety & PII gateway.

Provides a small, dependency-free pipeline that:
 1. Redacts common PII (email / phone / national ID / credit card).
 2. Blocks text when it matches an in-process blacklist (env-configurable).
 3. Records a SafetyEvent for auditability when either redaction or block occurs.

The implementation is intentionally conservative: we never hard-block
without explicit reason lists, and we prefer redaction over rejection
so that long-form task descriptions don't silently disappear.

Environment variables:
  SAFETY_BLACKLIST           comma-separated words/phrases that trigger a BLOCK
  SAFETY_PII_REDACT          "1" (default) redact PII, "0" leave as-is
  SAFETY_MAX_SNIPPET         int (default 400) max snippet length stored for audit
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session


EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
# Basic international phone (>= 8 digits, optional + and separators)
PHONE_RE = re.compile(r"(?<!\d)(\+?\d[\d\s\-]{7,18}\d)(?!\d)")
# Chinese national id (17 digits + [0-9X])
ID_CARD_RE = re.compile(r"(?<!\d)([1-9]\d{16}[\dXx])(?!\d)")
# Loose credit-card (13–19 digits, may have spaces/dashes)
CARD_RE = re.compile(r"(?<!\d)(?:\d[\s-]?){13,19}(?!\d)")


@dataclass
class SafetyResult:
    allowed: bool
    action: str  # "pass" | "redact" | "block"
    reasons: List[str] = field(default_factory=list)
    pii_types: List[str] = field(default_factory=list)
    redacted_text: str = ""
    original_length: int = 0
    detail: Dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "action": self.action,
            "reasons": list(self.reasons),
            "pii_types": list(self.pii_types),
            "redacted_preview": self.redacted_text[:120],
        }


def _env_list(name: str) -> List[str]:
    raw = (os.getenv(name) or "").strip()
    if not raw:
        return []
    return [w.strip().lower() for w in raw.split(",") if w.strip()]


def _blacklist() -> List[str]:
    extra = _env_list("SAFETY_BLACKLIST")
    # A small set of universally-unsafe terms; callers may extend via env.
    builtin = [
        # keep it short & non-offensive; real deployments must extend via env.
    ]
    return list({*builtin, *extra})


def _redact_enabled() -> bool:
    return (os.getenv("SAFETY_PII_REDACT", "1").strip() or "1") not in ("0", "false", "False")


def _max_snippet() -> int:
    try:
        return max(80, int(os.getenv("SAFETY_MAX_SNIPPET", "400")))
    except Exception:
        return 400


def _redact(text: str) -> tuple[str, List[str]]:
    found: List[str] = []
    out = text

    def _sub(pattern: re.Pattern[str], tag: str, replacement: str) -> None:
        nonlocal out
        if pattern.search(out):
            found.append(tag)
            out = pattern.sub(replacement, out)

    _sub(EMAIL_RE, "email", "[redacted-email]")
    _sub(ID_CARD_RE, "id_card", "[redacted-id]")
    _sub(CARD_RE, "card", "[redacted-card]")
    _sub(PHONE_RE, "phone", "[redacted-phone]")
    # de-duplicate preserving order
    seen, uniq = set(), []
    for t in found:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return out, uniq


def _blocklist_hits(text: str) -> List[str]:
    low = text.lower()
    hits: List[str] = []
    for word in _blacklist():
        if word and word in low:
            hits.append(f"blacklist:{word}")
    return hits


def check_text(
    text: Optional[str],
    *,
    source: str = "other",
    redact_pii: Optional[bool] = None,
) -> SafetyResult:
    """Evaluate the safety of a piece of user text.

    - Returns ``allowed=False`` only when a blacklist term matches.
    - PII is (by default) redacted, not blocked.
    - Empty/None text is always allowed.
    """
    if not text:
        return SafetyResult(allowed=True, action="pass", redacted_text="", original_length=0)

    raw = str(text)
    do_redact = _redact_enabled() if redact_pii is None else bool(redact_pii)

    reasons: List[str] = []
    pii: List[str] = []
    redacted = raw

    if do_redact:
        redacted, pii = _redact(raw)
        if pii:
            reasons.extend(f"pii:{t}" for t in pii)

    hits = _blocklist_hits(raw)
    if hits:
        reasons.extend(hits)
        return SafetyResult(
            allowed=False,
            action="block",
            reasons=reasons,
            pii_types=pii,
            redacted_text=redacted,
            original_length=len(raw),
            detail={"source": source},
        )

    if pii:
        return SafetyResult(
            allowed=True,
            action="redact",
            reasons=reasons,
            pii_types=pii,
            redacted_text=redacted,
            original_length=len(raw),
            detail={"source": source},
        )

    return SafetyResult(
        allowed=True,
        action="pass",
        reasons=reasons,
        pii_types=pii,
        redacted_text=redacted,
        original_length=len(raw),
        detail={"source": source},
    )


def record_event(
    db: Optional[Session],
    result: SafetyResult,
    *,
    source: str,
    user_id: Optional[int] = None,
    related_task_id: Optional[int] = None,
    snippet: Optional[str] = None,
) -> None:
    """Persist a SafetyEvent row for ``redact`` or ``block`` outcomes only.

    Uses an independent SessionLocal transaction so the audit row survives
    even when the caller subsequently raises HTTPException (which would
    otherwise roll back the request-scoped session).
    """
    if result.action == "pass":
        return
    try:
        from app.database.relational_db import SafetyEvent, SessionLocal  # local import

        ev = SafetyEvent(
            user_id=user_id,
            source=source,
            related_task_id=related_task_id,
            action=result.action,
            reasons=list(result.reasons),
            snippet=(snippet or result.redacted_text)[: _max_snippet()],
            pii_types=list(result.pii_types),
        )
        audit_db = SessionLocal()
        try:
            audit_db.add(ev)
            audit_db.commit()
        except Exception:
            try:
                audit_db.rollback()
            except Exception:
                pass
        finally:
            audit_db.close()
    except Exception:
        pass


def guard_text(
    db: Optional[Session],
    text: Optional[str],
    *,
    source: str,
    user_id: Optional[int] = None,
    related_task_id: Optional[int] = None,
    redact_pii: Optional[bool] = None,
) -> SafetyResult:
    """High-level helper: run the pipeline + audit. Returns the result.

    Callers decide whether to raise on ``not result.allowed``.
    """
    r = check_text(text, source=source, redact_pii=redact_pii)
    record_event(
        db,
        r,
        source=source,
        user_id=user_id,
        related_task_id=related_task_id,
        snippet=(text or "")[: _max_snippet()],
    )
    return r


def sanitize_text(
    db: Optional[Session],
    text: Optional[str],
    *,
    source: str,
    user_id: Optional[int] = None,
    related_task_id: Optional[int] = None,
) -> str:
    """Run the pipeline and return the safe (possibly redacted) text.

    Raises ``ValueError`` when a blacklist match forbids the text.
    """
    r = guard_text(
        db,
        text,
        source=source,
        user_id=user_id,
        related_task_id=related_task_id,
    )
    if not r.allowed:
        raise ValueError(f"content blocked by safety policy: {','.join(r.reasons)[:200]}")
    return r.redacted_text if r.action == "redact" else (text or "")
