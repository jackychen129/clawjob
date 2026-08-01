"""
Dispute AI pre-check (heuristic + optional LLM) — admin assist, not final ruling.

Benchmark: TaskForce AI jury (pre-screen only); AgentGigs admin + evidence snapshot.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.database.relational_db import Task


def _keyword_signals(text: str) -> List[str]:
    t = (text or "").lower()
    signals: List[str] = []
    if len((text or "").strip()) < 24:
        signals.append("reason_short")
    if any(w in t for w in ("未交付", "not delivered", "missing", "缺少", "未完成")):
        signals.append("delivery_dispute")
    if any(w in t for w in ("质量", "quality", "不符合", "does not meet", "验收")):
        signals.append("quality_dispute")
    if any(w in t for w in ("超时", "late", "deadline", "延期")):
        signals.append("timeline_dispute")
    if any(w in t for w in ("退款", "refund", "返点")):
        signals.append("refund_request")
    return signals


def _recommendation(signals: List[str], role_hint: str) -> str:
    if "delivery_dispute" in signals:
        return "request_delivery_proof"
    if "quality_dispute" in signals:
        return "compare_acceptance_criteria"
    if "refund_request" in signals:
        return "review_escrow_balance"
    if "reason_short" in signals:
        return "request_more_evidence"
    return "admin_review"


def _heuristic_precheck(
    task: Task,
    escrow: Dict[str, Any],
    *,
    initiator_role: str = "unknown",
) -> Dict[str, Any]:
    reason = str(escrow.get("dispute_reason") or "")
    evidence = escrow.get("dispute_evidence") if isinstance(escrow.get("dispute_evidence"), dict) else {}
    summary = str(evidence.get("summary") or "")
    combined = f"{reason}\n{summary}".strip()

    ms = escrow.get("milestones") or []
    idx = int(escrow.get("current_index", 0) or 0)
    criteria = ""
    milestone_title = ""
    if 0 <= idx < len(ms) and isinstance(ms[idx], dict):
        criteria = str(ms[idx].get("acceptance_criteria") or "")
        milestone_title = str(ms[idx].get("title") or f"Milestone {idx + 1}")

    signals = _keyword_signals(combined)
    if evidence.get("links") or evidence.get("attachments") or evidence.get("files"):
        signals.append("has_attachments")
    if criteria:
        signals.append("milestone_criteria_defined")
    else:
        signals.append("milestone_criteria_missing")

    rec = _recommendation(signals, initiator_role)
    confidence = 0.45
    if "has_attachments" in signals:
        confidence += 0.1
    if "milestone_criteria_defined" in signals:
        confidence += 0.08
    if "reason_short" in signals:
        confidence -= 0.12
    confidence = max(0.25, min(0.85, confidence))

    lines_zh = [
        f"任务 #{task.id} · 里程碑 {min(idx + 1, max(len(ms), 1))}/{max(len(ms), 1)}",
    ]
    if milestone_title:
        lines_zh.append(f"当前阶段：{milestone_title}")
    if criteria:
        lines_zh.append(f"验收要点：{criteria[:280]}{'…' if len(criteria) > 280 else ''}")
    lines_zh.append(f"争议摘要：{reason[:320]}{'…' if len(reason) > 320 else ''}")

    rec_zh = {
        "request_delivery_proof": "建议要求接取方补充交付物或验证链记录",
        "compare_acceptance_criteria": "建议对照里程碑验收要点与提交证据",
        "review_escrow_balance": "建议核对托管余额与里程碑放款记录",
        "request_more_evidence": "争议说明偏短，建议双方补充结构化证据",
        "admin_review": "建议人工综合 timeline 与验证链后裁决",
    }.get(rec, "建议人工审核")

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "heuristic",
        "initiator_role": initiator_role,
        "summary": "\n".join(lines_zh),
        "recommendation": rec,
        "recommendation_zh": rec_zh,
        "confidence": round(confidence, 2),
        "signals": signals,
        "milestone_index": idx,
        "milestone_criteria": criteria[:2000] if criteria else None,
    }


def _llm_enhance(base: Dict[str, Any], task: Task, escrow: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return base
    model = os.getenv("CLAWJOB_DISPUTE_LLM_MODEL", os.getenv("CLAWJOB_INTENT_LLM_MODEL", "gpt-4o-mini"))
    reason = str(escrow.get("dispute_reason") or "")[:1500]
    evidence = escrow.get("dispute_evidence") if isinstance(escrow.get("dispute_evidence"), dict) else {}
    criteria = base.get("milestone_criteria") or ""
    prompt = (
        "You are a dispute triage assistant for an agent task marketplace. "
        "Summarize the dispute in 2-3 concise Chinese sentences for an admin. "
        "Suggest one of: resume, force_confirm, request_more_evidence. "
        "Return JSON: {\"summary_zh\": \"...\", \"suggested_action\": \"...\", \"confidence\": 0.0-1.0}\n\n"
        f"Task title: {task.title}\nReason: {reason}\nEvidence: {json.dumps(evidence, ensure_ascii=False)[:1200]}\n"
        f"Acceptance criteria: {criteria[:800]}"
    )
    base_url = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1").rstrip("/")
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if parsed.get("summary_zh"):
            base = dict(base)
            base["summary"] = str(parsed["summary_zh"])[:2000]
            base["source"] = "llm"
            action = str(parsed.get("suggested_action") or "").strip()
            if action in ("resume", "force_confirm", "request_more_evidence"):
                base["recommendation"] = action
            if parsed.get("confidence") is not None:
                try:
                    base["confidence"] = round(float(parsed["confidence"]), 2)
                except (TypeError, ValueError):
                    pass
    except (urllib.error.URLError, KeyError, json.JSONDecodeError, IndexError, ValueError):
        pass
    return base


def build_dispute_precheck(
    task: Task,
    escrow: Dict[str, Any],
    *,
    initiator_role: str = "unknown",
    use_llm: bool = False,
) -> Dict[str, Any]:
    base = _heuristic_precheck(task, escrow, initiator_role=initiator_role)
    if use_llm and os.getenv("OPENAI_API_KEY", "").strip():
        base = _llm_enhance(base, task, escrow)
    return base
