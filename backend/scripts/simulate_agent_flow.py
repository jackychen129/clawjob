"""
End-to-end simulation script that drives the full Agent lifecycle.

Run with (from backend/):
    python3 scripts/simulate_agent_flow.py

It exercises in-process via fastapi.testclient.TestClient so it does not
need the app to be running on a port. Failures are collected and printed
at the end; exit code is non-zero if any step fails so this can be
wired into CI.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

HERE = os.path.dirname(os.path.abspath(__file__))
BACKEND = os.path.abspath(os.path.join(HERE, ".."))
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)

os.environ.setdefault("VERIFICATION_CODE_DEV", "123456")
os.environ.setdefault("SAFETY_BLACKLIST", "forbidden_keyword_sim")

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.database.relational_db import init_db  # noqa: E402


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


init_db()
CLIENT = TestClient(app)

_failures: List[str] = []
_steps: List[Tuple[str, str]] = []


def _tag() -> str:
    return str(int(time.time() * 1000) % 10_000_000)


def step(label: str) -> None:
    banner = f"\n=== STEP: {label} ==="
    print(banner, flush=True)
    _steps.append((label, "start"))


def ok(msg: str) -> None:
    print(f"  [ok] {msg}", flush=True)


def fail(msg: str, detail: str = "") -> None:
    out = f"  [FAIL] {msg}"
    if detail:
        out += f"\n        {detail}"
    print(out, flush=True)
    _failures.append(f"{msg}: {detail}" if detail else msg)


def expect(cond: bool, msg: str, detail: str = "") -> bool:
    if cond:
        ok(msg)
        return True
    fail(msg, detail)
    return False


def req(method: str, path: str, *, token: Optional[str] = None, **kw) -> Tuple[int, Any, str]:
    headers = dict(kw.pop("headers", {}) or {})
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = CLIENT.request(method, path, headers=headers, **kw)
    ctype = r.headers.get("content-type", "")
    try:
        body = r.json() if "application/json" in ctype else r.text
    except Exception:
        body = r.text
    return r.status_code, body, r.text


def register(username: str, email: str, password: str = "pw12345") -> Optional[str]:
    s, _, t = req("POST", "/auth/send-verification-code", json={"email": email})
    if s != 200:
        fail(f"send-verification-code for {email}", t)
        return None
    s, body, t = req(
        "POST",
        "/auth/register",
        json={
            "username": username,
            "email": email,
            "password": password,
            "verification_code": os.environ["VERIFICATION_CODE_DEV"],
        },
    )
    if s != 200:
        fail(f"register {username}", t)
        return None
    return (body or {}).get("access_token")


def make_admin(username: str) -> Optional[str]:
    token = register(username, f"{username}@example.com")
    if not token:
        return None
    from app.database.relational_db import SessionLocal, User
    db = SessionLocal()
    try:
        u = db.query(User).filter(User.username == username).first()
        if not u:
            fail(f"elevate admin {username}", "user row missing")
            return None
        u.is_superuser = True
        db.commit()
    finally:
        db.close()
    return token


# -----------------------------------------------------------------------------
# Scenario
# -----------------------------------------------------------------------------


def run() -> int:
    tag = _tag()
    pub = f"simpub_{tag}"
    exe = f"simexe_{tag}"
    admin = f"simadm_{tag}"

    step("register publisher / executor / admin")
    tk_pub = register(pub, f"{pub}@example.com")
    tk_exe = register(exe, f"{exe}@example.com")
    tk_adm = make_admin(admin)
    if not (tk_pub and tk_exe and tk_adm):
        return 1

    step("publisher recharges 200 credits")
    s, body, t = req("POST", "/account/recharge", token=tk_pub, json={"amount": 200})
    expect(s == 200, "recharge", t)

    step("executor registers an Agent")
    s, body, t = req(
        "POST",
        "/agents/register",
        token=tk_exe,
        json={"name": f"sim-agent-{tag}", "description": "simulated agent"},
    )
    expect(s == 200, "agent register", t)
    agent_id = (body or {}).get("id")

    step("safety pipeline rejects forbidden content on publish")
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": "safe-title",
            "description": "we need forbidden_keyword_sim done today",
        },
    )
    expect(s == 400, "safety block returns 400", t)
    expect("内容安全" in t, "error message mentions safety policy", t)

    step("safety pipeline redacts PII in task description")
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": "pii-check",
            "description": "contact me at foo@example.com or +1 415 555 9999",
        },
    )
    expect(s == 200, "pii publish", t)
    task_pii = (body or {}).get("id")
    # re-fetch
    s, detail, t = req("GET", f"/tasks/{task_pii}", token=tk_pub)
    if s == 200 and isinstance(detail, dict):
        desc = detail.get("description") or ""
        expect("foo@example.com" not in desc, "email redacted in stored description", desc[:120])
        expect("[redacted-email]" in desc or "foo@example.com" not in desc, "redaction token present", desc[:120])
    else:
        fail("fetch pii task detail", t)

    step("publish a paid task (with completion webhook)")
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": f"sim-task-{tag}",
            "description": "compose a short haiku",
            "reward_points": 20,
            "completion_webhook_url": "https://example.com/webhook",
            "category": "writing",
        },
    )
    expect(s == 200, "publish paid task", t)
    task_id = (body or {}).get("id")

    step("executor subscribes to the task")
    s, body, t = req(
        "POST",
        f"/tasks/{task_id}/subscribe",
        token=tk_exe,
        json={"agent_id": agent_id},
    )
    expect(s == 200, "subscribe", t)

    step("execute the task with step replay + sandbox quota")
    async def ok_exec(tid):
        return {"ok": True, "output": f"haiku for {tid}"}

    with patch("app.main.task_system.execute_task", side_effect=ok_exec):
        s, body, t = req("POST", f"/tasks/{task_id}/execute", token=tk_pub)
    expect(s == 200, "execute ok", t)
    run_id = (body or {}).get("run_id") if isinstance(body, dict) else None
    expect(isinstance(run_id, str) and len(run_id) > 0, "run_id returned", str(body)[:200])

    if run_id:
        step("verify step replay endpoints")
        s, runs, t = req("GET", f"/tasks/{task_id}/runs", token=tk_pub)
        expect(s == 200, "list runs", t)
        if isinstance(runs, dict):
            expect(any(r.get("run_id") == run_id for r in runs.get("items", [])), "run_id present in list")

        s, steps_body, t = req("GET", f"/tasks/{task_id}/runs/{run_id}/steps", token=tk_pub)
        expect(s == 200, "list steps", t)
        if isinstance(steps_body, dict):
            kinds = [s["kind"] for s in steps_body.get("steps", [])]
            expect("start" in kinds and "end" in kinds, "steps contain start/end", str(kinds))

        s, exp_body, t = req("GET", f"/tasks/{task_id}/runs/{run_id}/export", token=tk_pub)
        expect(s == 200, "export run", t)

    step("sandbox rejects long-running execute (quota_exceeded)")
    # Prepare a second task and tighten its quota
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={"title": f"sim-slow-{tag}", "description": "tight quota"},
    )
    if s == 200:
        slow_id = body["id"]
        from app.database.relational_db import SessionLocal, Task
        from sqlalchemy.orm.attributes import flag_modified
        db = SessionLocal()
        try:
            row = db.query(Task).filter(Task.id == slow_id).first()
            data = dict(row.input_data or {})
            data["execution_quota"] = {"max_duration_seconds": 1}
            row.input_data = data
            flag_modified(row, "input_data")
            db.commit()
        finally:
            db.close()

        import asyncio as _asyncio
        async def slow_exec(tid):
            await _asyncio.sleep(3)
            return {"ok": True}

        with patch("app.main.task_system.execute_task", side_effect=slow_exec):
            s2, body2, t2 = req("POST", f"/tasks/{slow_id}/execute", token=tk_pub)
        expect(s2 == 429, "quota exceeded returns 429", t2)
        expect("quota_exceeded" in t2 or "沙箱" in t2, "error mentions quota", t2)
    else:
        fail("publish slow task", t)

    step("executor submits completion (mock webhook)")
    with patch("app.main.httpx") as mocked:
        mocked.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
        s, body, t = req(
            "POST",
            f"/tasks/{task_id}/submit-completion",
            token=tk_exe,
            json={"result_summary": "delivered haiku, contact: ops@example.com"},
        )
    expect(s == 200, "submit completion", t)

    step("publisher confirms acceptance")
    s, body, t = req("POST", f"/tasks/{task_id}/confirm", token=tk_pub)
    expect(s == 200, "confirm", t)

    step("task final state is completed")
    s, body, t = req("GET", f"/tasks/{task_id}", token=tk_pub)
    if isinstance(body, dict):
        expect(body.get("status") == "completed", "status=completed", f"actual={body.get('status')}")

    step("executor receives reward (credits increased)")
    s, body, t = req("GET", "/account/me", token=tk_exe)
    if isinstance(body, dict):
        expect((body.get("credits") or 0) > 0, "executor credits > 0", str(body.get("credits")))
    else:
        fail("account/me", t)

    step("agent case studies expose the completed task")
    s, body, t = req("GET", f"/agents/{agent_id}/cases")
    if isinstance(body, dict):
        expect(any(c.get("task_id") == task_id for c in body.get("cases", [])), "completed task in case list")
    else:
        fail("agent cases", t)

    step("public user profile reachable via /u/{username}")
    s, body, t = req("GET", f"/u/{exe}")
    expect(s == 200, "public user page", t)
    if isinstance(body, dict):
        expect(body.get("username") == exe, "profile username matches")
        expect("credits" not in body, "sensitive field 'credits' hidden")

    step("publisher insights reports recent spend")
    s, body, t = req("GET", "/account/insights", token=tk_pub)
    if isinstance(body, dict):
        expect(body.get("tasks", {}).get("total", 0) >= 1, "insights tasks >= 1")
        expect(body.get("spent_points", 0) >= 20, "insights spent >= 20")
    else:
        fail("account/insights", t)

    step("admin platform insights reachable")
    s, body, t = req("GET", "/admin/insights/platform", token=tk_adm)
    if isinstance(body, dict):
        expect("funnel" in body and "gmv" in body, "platform insights fields present")
    else:
        fail("admin platform insights", t)

    step("admin safety events records the earlier block")
    s, body, t = req("GET", "/admin/safety/events", token=tk_adm, params={"action": "block"})
    if isinstance(body, dict):
        items = body.get("items", [])
        expect(any("blacklist:" in (r.get("reasons") or [None])[0] for r in items if r.get("reasons")),
               "a blacklist block event is recorded")
    else:
        fail("admin safety events", t)

    step("audit log export produces a zip")
    s, _body, _t = req("GET", "/admin/audit/export", token=tk_adm)
    expect(s == 200, "audit export returns 200", _t[:200] if isinstance(_t, str) else "")

    # ---------------------------------------------------------------
    # Extended scenarios
    # ---------------------------------------------------------------

    step("cancel refund: publish + immediate cancel returns credits")
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": f"sim-cancel-{tag}",
            "description": "will be cancelled",
            "reward_points": 10,
            "completion_webhook_url": "https://example.com/webhook",
        },
    )
    if s != 200:
        fail("publish cancel task", t)
    else:
        cancel_task_id = body["id"]
        s0, me0, _ = req("GET", "/account/me", token=tk_pub)
        before = (me0 or {}).get("credits", 0) if isinstance(me0, dict) else 0
        s, body, t = req("POST", f"/tasks/{cancel_task_id}/cancel", token=tk_pub)
        expect(s == 200, "cancel task", t)
        s1, me1, _ = req("GET", "/account/me", token=tk_pub)
        after = (me1 or {}).get("credits", 0) if isinstance(me1, dict) else 0
        expect(after >= before + 10, "credits refunded", f"{before} -> {after}")
        # cancel twice should be idempotent / 400
        s, body, t = req("POST", f"/tasks/{cancel_task_id}/cancel", token=tk_pub)
        expect(s in (200, 400, 409), "double cancel is safe", t)

    step("reverse auction: publish -> bid -> accept -> complete")
    import datetime as _dt
    deadline = (_dt.datetime.utcnow() + _dt.timedelta(hours=1)).isoformat() + "Z"
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": f"sim-auction-{tag}",
            "description": "open auction demo",
            "reward_points": 30,
            "completion_webhook_url": "https://example.com/webhook",
            "auction": {
                "enabled": True,
                "min_reward": 10,
                "max_reward": 30,
                "deadline": deadline,
                "auto_pick": "manual",
            },
        },
    )
    expect(s == 200, "publish auction task", t)
    auction_task_id = (body or {}).get("id") if isinstance(body, dict) else None

    if auction_task_id:
        # executor places bid
        s, body, t = req(
            "POST",
            f"/tasks/{auction_task_id}/bids",
            token=tk_exe,
            json={"agent_id": agent_id, "price": 20, "eta_hours": 4, "proposal": "I can ship fast"},
        )
        expect(s == 200, "place bid", t)
        bid_id = None
        if isinstance(body, dict):
            if isinstance(body.get("bid"), dict):
                bid_id = body["bid"].get("id")
            elif isinstance(body.get("id"), int):
                bid_id = body["id"]
        # list bids
        s, body, t = req("GET", f"/tasks/{auction_task_id}/bids", token=tk_pub)
        if isinstance(body, dict):
            bids = body.get("bids") or body.get("items") or []
            expect(any(
                (b.get("id") == bid_id) or (b.get("bid_id") == bid_id) for b in bids
            ), "bid is visible to publisher")
        # publisher accepts bid
        if bid_id:
            s, body, t = req(
                "POST",
                f"/tasks/{auction_task_id}/bids/{bid_id}/accept",
                token=tk_pub,
            )
            expect(s == 200, "accept bid", t)
        # executor submits + publisher confirms
        with patch("app.main.httpx") as mocked:
            mocked.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
            s, body, t = req(
                "POST",
                f"/tasks/{auction_task_id}/submit-completion",
                token=tk_exe,
                json={"result_summary": "auction task done"},
            )
            expect(s == 200, "auction submit completion", t)
        s, body, t = req("POST", f"/tasks/{auction_task_id}/confirm", token=tk_pub)
        expect(s == 200, "auction confirm", t)

    step("referral flow: invitee registers with code, completes a task, bonus granted")
    # get my referral code
    s, body, t = req("GET", "/account/referral", token=tk_pub)
    expect(s == 200, "fetch referral summary", t)
    ref_code = (body or {}).get("referral_code") if isinstance(body, dict) else None
    if ref_code:
        invitee_name = f"siminv_{tag}"
        # invitee register with referral_code
        s0, _, _ = req("POST", "/auth/send-verification-code", json={"email": f"{invitee_name}@example.com"})
        s, body, t = req(
            "POST",
            "/auth/register",
            json={
                "username": invitee_name,
                "email": f"{invitee_name}@example.com",
                "password": "pw12345",
                "verification_code": os.environ["VERIFICATION_CODE_DEV"],
                "referral_code": ref_code,
            },
        )
        expect(s == 200, "invitee register with referral_code", t)
        tk_inv = (body or {}).get("access_token") if isinstance(body, dict) else None
        if tk_inv:
            # publisher creates a task, invitee's agent picks it up and completes
            s, body, _ = req(
                "POST",
                "/agents/register",
                token=tk_inv,
                json={"name": f"inv-agent-{tag}", "description": "invited agent"},
            )
            inv_agent_id = (body or {}).get("id") if isinstance(body, dict) else None
            s, body, _ = req(
                "POST",
                "/tasks",
                token=tk_pub,
                json={
                    "title": f"sim-refbonus-{tag}",
                    "description": "first task for invitee",
                    "reward_points": 15,
                    "completion_webhook_url": "https://example.com/webhook",
                },
            )
            ref_task_id = (body or {}).get("id") if isinstance(body, dict) else None
            if inv_agent_id and ref_task_id:
                req("POST", f"/tasks/{ref_task_id}/subscribe", token=tk_inv,
                    json={"agent_id": inv_agent_id})
                with patch("app.main.httpx") as mocked:
                    mocked.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
                    req("POST", f"/tasks/{ref_task_id}/submit-completion", token=tk_inv,
                        json={"result_summary": "first completion"})
                req("POST", f"/tasks/{ref_task_id}/confirm", token=tk_pub)
                s, body, t = req("GET", "/account/referral/records", token=tk_pub)
                if isinstance(body, dict):
                    records = body.get("records", []) or body.get("items", [])
                    expect(
                        any(r.get("invitee_username") == invitee_name for r in records),
                        "invitee shown in referral records",
                        str(records)[:300],
                    )
                    expect(
                        any(r.get("invitee_username") == invitee_name and r.get("status") == "rewarded"
                            for r in records),
                        "invitee marked rewarded after first task",
                        str(records)[:300],
                    )
                    # referrer's credit should increase from bonus
                    s, body, _ = req("GET", "/account/referral", token=tk_pub)
                    if isinstance(body, dict):
                        expect(
                            int(body.get("total_reward_points", 0) or 0) > 0,
                            "total_reward_points > 0 on referrer summary",
                            str(body),
                        )

    step("candidate recommendation returns a ranked list")
    s, body, t = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": f"sim-rec-{tag}",
            "description": "who can do data cleaning",
            "skills": ["data-clean"],
        },
    )
    if s == 200:
        rec_task_id = body["id"]
        s, body, t = req("GET", f"/tasks/{rec_task_id}/recommend-candidates", token=tk_pub,
                         params={"k": 3})
        expect(s == 200, "recommend-candidates ok", t)
        if isinstance(body, dict):
            expect(isinstance(body.get("candidates"), list) or isinstance(body.get("items"), list),
                   "recommendation returns a list")

    step("submit completion redacts PII before delivery")
    # publish a fresh task -> subscribe -> submit with an email address
    s, body, _ = req(
        "POST",
        "/tasks",
        token=tk_pub,
        json={
            "title": f"sim-submitpii-{tag}",
            "description": "pii in submission",
            "reward_points": 5,
            "completion_webhook_url": "https://example.com/webhook",
        },
    )
    if s == 200:
        t2 = body["id"]
        req("POST", f"/tasks/{t2}/subscribe", token=tk_exe, json={"agent_id": agent_id})
        with patch("app.main.httpx") as mocked:
            mocked.Client.return_value.__enter__.return_value.post.return_value.status_code = 200
            sc, body2, txt = req(
                "POST",
                f"/tasks/{t2}/submit-completion",
                token=tk_exe,
                json={"result_summary": "ship to me at ship@example.com asap"},
            )
        expect(sc == 200, "submit-completion with PII", txt)
        # fetch task detail and verify summary is redacted
        s, detail, _ = req("GET", f"/tasks/{t2}", token=tk_pub)
        if isinstance(detail, dict):
            odata = detail.get("output_data") or {}
            summary = ""
            if isinstance(odata, dict):
                # summary is usually kept in output_data.result_summary or pending_verification
                for k in ("result_summary", "pending_verification", "completion_summary"):
                    v = odata.get(k)
                    if isinstance(v, str):
                        summary = v
                        break
                    if isinstance(v, dict) and isinstance(v.get("result_summary"), str):
                        summary = v["result_summary"]
                        break
            expect("ship@example.com" not in summary,
                   "submission email redacted in stored output",
                   summary[:160])
        req("POST", f"/tasks/{t2}/confirm", token=tk_pub)

    # ---------------------------------------------------------------
    # Wave: KYC / Withdrawal / Workspace / RFQ / Subscription / Skill revenue
    # ---------------------------------------------------------------

    step("KYC: unapproved user cannot withdraw, reject blocks, admin approve unblocks")
    s, body, t = req("GET", "/account/kyc", token=tk_exe)
    expect(s == 200, "fetch my kyc status", t)
    if isinstance(body, dict):
        expect(body.get("kyc_status") in ("none", "unverified", "pending", "approved", "rejected"),
               "kyc_status field", str(body))

    s, _, t = req(
        "PATCH",
        "/account/receiving-account",
        token=tk_exe,
        json={"account_type": "bank_card", "account_name": "执行者", "account_number": "6222000011112222"},
    )
    expect(s == 200, "bind receiving account", t)

    # Withdraw before approval -> blocked
    s, body, t = req("POST", "/account/withdrawals", token=tk_exe, json={"amount": 100})
    expect(s in (400, 403), "withdraw blocked when not KYC approved", t)

    # Submit personal KYC
    s, body, t = req(
        "POST",
        "/account/kyc/personal",
        token=tk_exe,
        json={
            "legal_name": "张三",
            "id_type": "id_card",
            "id_number": "310000199001010000",
            "country": "CN",
            "contact_phone": "13800000000",
        },
    )
    expect(s == 200, "submit personal kyc", t)
    kyc_rec = (body or {}).get("kyc") if isinstance(body, dict) else None
    kyc_id = (kyc_rec or {}).get("id") if isinstance(kyc_rec, dict) else None

    if kyc_id:
        s, body, t = req(
            "POST",
            f"/admin/kyc/records/{kyc_id}/reject",
            token=tk_adm,
            json={"reason": "blurry photo"},
        )
        expect(s == 200, "admin rejects kyc", t)
        s, body, t = req("GET", "/account/kyc", token=tk_exe)
        if isinstance(body, dict):
            expect(body.get("kyc_status") == "rejected",
                   "kyc_status=rejected after reject", str(body))

        # Resubmit + approve
        s, body, t = req(
            "POST",
            "/account/kyc/personal",
            token=tk_exe,
            json={
                "legal_name": "张三",
                "id_type": "id_card",
                "id_number": "310000199001010000",
                "country": "CN",
                "contact_phone": "13800000000",
            },
        )
        expect(s == 200, "resubmit personal kyc", t)
        kyc_rec = (body or {}).get("kyc") if isinstance(body, dict) else None
        new_kyc_id = (kyc_rec or {}).get("id") if isinstance(kyc_rec, dict) else None
        if new_kyc_id:
            s, body, t = req("POST", f"/admin/kyc/records/{new_kyc_id}/approve",
                             token=tk_adm, json={})
            expect(s == 200, "admin approves kyc", t)
            s, body, t = req("GET", "/account/kyc", token=tk_exe)
            if isinstance(body, dict):
                expect(body.get("kyc_status") == "approved",
                       "kyc_status=approved after approve", str(body))

    step("KYC gate: approved user can withdraw, admin can mark paid")
    from app.database.relational_db import SessionLocal as _SL, User as _User
    _db = _SL()
    try:
        _u = _db.query(_User).filter(_User.username == exe).first()
        if _u:
            _u.commission_balance = float((_u.commission_balance or 0) + 100)
            _db.commit()
    finally:
        _db.close()

    s, body, t = req("POST", "/account/withdrawals", token=tk_exe, json={"amount": 50})
    expect(s == 200, "withdraw after KYC approval", t)
    wd_id = (body or {}).get("withdrawal_id") if isinstance(body, dict) else None

    s, body, t = req("GET", "/account/withdrawals", token=tk_exe)
    if isinstance(body, dict):
        wl = body.get("withdrawals") or body.get("items") or []
        expect(any(w.get("id") == wd_id for w in wl),
               "withdrawal record visible", str(wl)[:200])

    s, body, t = req("GET", "/admin/withdrawals", token=tk_adm, params={"status": "pending"})
    expect(s == 200, "admin lists pending withdrawals", t)
    if wd_id:
        s, body, t = req(
            "POST",
            f"/admin/withdrawals/{wd_id}/decide",
            token=tk_adm,
            json={"action": "mark_paid", "note": "wired"},
        )
        expect(s == 200, "admin marks withdrawal paid", t)

    step("Workspace: create, invite, role gate, recharge, RFQ batch publish")
    # Team plan requires business KYC on owner; submit + approve
    s, body, t = req(
        "POST",
        "/account/kyc/business",
        token=tk_pub,
        json={
            "business_name": "ACME Corp",
            "business_id": "REG-ACME-001",
            "legal_name": "ACME 运营总监",
            "country": "CN",
            "contact_phone": "13800000001",
        },
    )
    expect(s == 200, "publisher submits business kyc", t)
    if isinstance(body, dict):
        kyc_rec = body.get("kyc") or {}
        b_kyc_id = kyc_rec.get("id") if isinstance(kyc_rec, dict) else None
    else:
        b_kyc_id = None
    if b_kyc_id:
        req("POST", f"/admin/kyc/records/{b_kyc_id}/approve", token=tk_adm, json={})

    s, body, t = req(
        "POST",
        "/workspaces",
        token=tk_pub,
        json={"name": f"ACME-{tag}", "plan": "team"},
    )
    expect(s == 200, "create team workspace", t)
    ws_id = (body or {}).get("id") if isinstance(body, dict) else None

    if ws_id:
        s, body, t = req("GET", "/workspaces/mine", token=tk_pub)
        expect(s == 200, "list my workspaces", t)
        # Invite executor as publisher
        s, body, t = req(
            "POST",
            f"/workspaces/{ws_id}/invite",
            token=tk_pub,
            json={"email": f"{exe}@example.com", "role": "publisher"},
        )
        expect(s == 200, "invite executor", t)
        invite_token = (body or {}).get("token") if isinstance(body, dict) else None
        if invite_token:
            s, body, t = req(
                "POST",
                "/workspaces/accept-invite",
                token=tk_exe,
                json={"token": invite_token},
            )
            expect(s == 200, "executor accepts invite", t)

        # Recharge workspace (owner allowed)
        s, body, t = req(
            "POST",
            f"/workspaces/{ws_id}/recharge",
            token=tk_pub,
            json={"amount": 500},
        )
        expect(s == 200, "recharge workspace", t)

        # Non-billing role cannot recharge
        stranger2 = f"sim_ws_outsider_{tag}"
        tk_out = register(stranger2, f"{stranger2}@example.com")
        if tk_out:
            s, body, t = req(
                "POST",
                f"/workspaces/{ws_id}/recharge",
                token=tk_out,
                json={"amount": 10},
            )
            expect(s in (403, 404), "outsider cannot recharge workspace", t)

        # RFQ preview + submit
        rfq_items = [
            {"title": f"rfq-a-{tag}", "description": "analyse sales", "reward_points": 20},
            {"title": f"rfq-b-{tag}", "description": "draft weekly report", "reward_points": 25},
            {"title": f"rfq-c-{tag}", "description": "benchmark competitor",
             "reward_points": 30, "category": "research"},
        ]
        # RFQ items need completion_webhook_url when reward_points>0
        for it in rfq_items:
            it["completion_webhook_url"] = "https://example.com/webhook"
        s, body, t = req(
            "POST",
            f"/workspaces/{ws_id}/rfq/preview",
            token=tk_pub,
            json={"items": rfq_items},
        )
        expect(s == 200, "rfq preview", t)
        if isinstance(body, dict):
            expect(int(body.get("credits_required", 0) or 0) == 75,
                   "rfq preview credits_required = 75",
                   str(body))

        s, body, t = req(
            "POST",
            f"/workspaces/{ws_id}/rfq/submit",
            token=tk_pub,
            json={"items": rfq_items},
        )
        expect(s == 200, "rfq submit", t)
        if isinstance(body, dict):
            created = body.get("tasks") or body.get("created") or []
            expect(len(created) == 3, "rfq created 3 tasks", str(body))

        # Safety: blacklist keyword should block RFQ submit
        bad_items = [
            {"title": f"rfq-bad-{tag}", "description": "needs forbidden_keyword_sim done"},
        ]
        s, body, t = req(
            "POST",
            f"/workspaces/{ws_id}/rfq/submit",
            token=tk_pub,
            json={"items": bad_items},
        )
        expect(s == 400, "rfq safety block returns 400", t)

    step("Subscriptions: plans catalog + subscribe pro + cancel reverts to free")
    s, body, t = req("GET", "/subscriptions/plans")
    expect(s == 200, "list plans public", t)
    if isinstance(body, dict):
        plans = body.get("plans") or body.get("items") or []
        expect(any((p.get("code") or p.get("tier")) == "pro" for p in plans),
               "pro plan exposed", str(plans)[:200])

    req("POST", "/account/recharge", token=tk_pub, json={"amount": 5000})
    s, body, t = req(
        "POST", "/account/subscription/subscribe", token=tk_pub, json={"plan_code": "pro"}
    )
    expect(s == 200, "subscribe pro", t)
    s, body, t = req("GET", "/account/subscription", token=tk_pub)
    if isinstance(body, dict):
        expect((body.get("tier") or body.get("plan_code")) == "pro",
               "tier=pro after subscribe", str(body))
    s, body, t = req("POST", "/account/subscription/cancel", token=tk_pub, json={})
    expect(s == 200, "cancel subscription", t)
    s, body, t = req("GET", "/account/subscription", token=tk_pub)
    if isinstance(body, dict):
        expect((body.get("tier") or body.get("plan_code") or "free") in ("free", None),
               "tier reverts to free", str(body))

    step("Skill revenue: author sets pricing, charge splits author + platform")
    from app.database.relational_db import SessionLocal as _SL2, PublishedSkill
    import secrets as _secrets
    _db = _SL2()
    try:
        exe_user = _db.query(_User).filter(_User.username == exe).first()
        skill_token = f"sim_sk_{tag}_{_secrets.token_hex(3)}"
        sk = PublishedSkill(
            skill_token=skill_token,
            name=f"sim-skill-{tag}",
            description="noop",
        )
        if exe_user:
            sk.author_user_id = exe_user.id
        _db.add(sk)
        _db.commit()
        _db.refresh(sk)
    finally:
        _db.close()

    s, body, t = req(
        "POST",
        f"/skills/{skill_token}/pricing",
        token=tk_exe,
        json={
            "pricing_model": "per_download",
            "price_per_unit": 10,
            "revenue_share_bp": 7000,
        },
    )
    expect(s == 200, "author sets pricing", t)

    # Non-author cannot update pricing
    stranger3 = f"sim_sk_outsider_{tag}"
    tk_out2 = register(stranger3, f"{stranger3}@example.com")
    if tk_out2:
        s, body, t = req(
            "POST",
            f"/skills/{skill_token}/pricing",
            token=tk_out2,
            json={"pricing_model": "per_download", "price_per_unit": 1},
        )
        expect(s in (403, 404), "non-author cannot set pricing", t)

    # Ensure publisher has credits for charge
    req("POST", "/account/recharge", token=tk_pub, json={"amount": 100})
    s, body, t = req(
        "POST",
        f"/skills/{skill_token}/charge",
        token=tk_pub,
        params={"event_kind": "download"},
    )
    expect(s == 200, "charge skill download", t)

    s, body, t = req("GET", "/account/skill-revenue", token=tk_exe)
    if isinstance(body, dict):
        items = body.get("items") or body.get("records") or []
        expect(len(items) >= 1, "author sees at least one revenue record",
               str(items)[:200])

    step("non-owner cannot read another user's task run list")
    if run_id:
        stranger = f"simstr_{tag}"
        tk_s = register(stranger, f"{stranger}@example.com")
        s, _, t = req("GET", f"/tasks/{task_id}/runs", token=tk_s)
        expect(s == 403, "stranger gets 403 on runs", t)
        s, _, t = req("GET", f"/tasks/{task_id}/runs/{run_id}/steps", token=tk_s)
        expect(s == 403, "stranger gets 403 on step detail", t)

    # Summary
    print("\n" + "=" * 60)
    if _failures:
        print(f"FAILED with {len(_failures)} issue(s):")
        for f in _failures:
            print(f"  - {f}")
        return 2
    print("ALL SIMULATION STEPS PASSED")
    return 0


if __name__ == "__main__":
    try:
        rc = run()
    except Exception:
        traceback.print_exc()
        rc = 3
    sys.exit(rc)
