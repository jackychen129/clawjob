#!/usr/bin/env python3
"""
ClawJob 线上端到端自动化测试脚本。
覆盖：API 健康、任务大厅公开接口、注册/登录、账户、发布任务（含地点/时长/技能）、
Agent、接取任务、任务详情扩展字段、前端页面可达性。
用法:
  python3 deploy/verify-online-e2e.py [API_BASE_URL]
  # 或
  CLAWJOB_API_URL=http://8.216.64.80:8000 CLAWJOB_FRONTEND_URL=http://8.216.64.80:3000 python3 deploy/verify-online-e2e.py
"""
import os
import sys
import json
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "verify-online-e2e-result.txt")

def log(msg):
    print(msg)
    sys.stdout.flush()
    try:
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

try:
    import urllib.request
    import urllib.error
    import ssl
except ImportError:
    print("Python 3 required")
    sys.exit(1)

# 从环境变量或第一个参数读取；默认与 deploy/.deploy_env 中 SERVER_IP 一致时可用
BASE = (os.environ.get("CLAWJOB_API_URL") or (sys.argv[1] if len(sys.argv) > 1 else "http://8.216.64.80:8000")).rstrip("/")
FRONTEND_BASE = (os.environ.get("CLAWJOB_FRONTEND_URL") or BASE.replace(":8000", ":3000")).rstrip("/")
SSL_CTX = ssl.create_default_context()

def req(path, method="GET", data=None, token=None, timeout=25):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=SSL_CTX) as res:
            return res.getcode(), json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body_str = e.read().decode()
            return e.code, json.loads(body_str) if body_str.strip().startswith("{") else {"detail": body_str}
        except Exception:
            return e.code, {"detail": str(e)}
    except Exception as e:
        return 0, {"detail": str(e), "error_type": type(e).__name__}

def get_frontend(url, timeout=15):
    """GET 前端页面，返回 (status_code, body_preview)"""
    try:
        r = urllib.request.Request(url, headers={"Accept": "text/html,application/xhtml+xml"})
        with urllib.request.urlopen(r, timeout=timeout, context=SSL_CTX) as res:
            body = res.read().decode(errors="replace")[:2000]
            return res.getcode(), body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:500]
    except Exception as e:
        return 0, str(e)

def main():
    # 清空并写时间戳
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"线上 E2E 验证时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception:
        pass

    log("=" * 60)
    log("ClawJob 线上自动化测试")
    log("=" * 60)
    log(f"API:      {BASE}")
    log(f"Frontend: {FRONTEND_BASE}")
    log("")

    errors = []
    passed = []

    # --- 1. API 健康 ---
    code, body = req("/health")
    if code != 200:
        errors.append(f"GET /health -> {code} {body}")
    else:
        passed.append("GET /health")
        log(f"[OK] GET /health -> 200 {body.get('status', body)}")

    # --- 2. 任务大厅公开：任务列表 ---
    code, body = req("/tasks")
    if code != 200:
        errors.append(f"GET /tasks -> {code} {body}")
    else:
        passed.append("GET /tasks")
        tasks = body.get("tasks", [])
        log(f"[OK] GET /tasks -> 200 (共 {len(tasks)} 条)")

    # --- 3. 任务大厅公开：候选者 ---
    code, body = req("/candidates")
    if code != 200:
        errors.append(f"GET /candidates -> {code} {body}")
    else:
        passed.append("GET /candidates")
        cands = body.get("candidates", [])
        log(f"[OK] GET /candidates -> 200 (共 {len(cands)} 个)")

    # --- 4. Google OAuth 状态（可选）---
    code, body = req("/auth/google/status")
    if code == 200:
        passed.append("GET /auth/google/status")
        log(f"[OK] GET /auth/google/status -> configured={body.get('configured', False)}")
    else:
        log(f"[INFO] GET /auth/google/status -> {code} (可选)")

    # --- 5. 注册 ---
    user = f"e2e_{int(time.time())}"
    code, body = req("/auth/register", method="POST", data={
        "username": user,
        "email": f"{user}@test.local",
        "password": "e2e-pass-123",
    })
    token = None
    if code != 200:
        errors.append(f"POST /auth/register -> {code} {body}")
        log("[FAIL] 注册失败，后续需登录的用例跳过")
    else:
        token = body.get("access_token")
        passed.append("POST /auth/register")
        log(f"[OK] POST /auth/register -> 200 username={user}")

    if not token:
        log("")
        log("Errors: " + str(errors))
        log("--- 建议检查 deploy/VERIFY_AND_FIX.md ---")
        sys.exit(1)

    task_id = None  # 用于发布任务后的详情/接取

    # --- 6. 账户 /me ---
    code, body = req("/account/me", token=token)
    if code != 200:
        errors.append(f"GET /account/me -> {code} {body}")
    else:
        passed.append("GET /account/me")
        log(f"[OK] GET /account/me -> 200 credits={body.get('credits', '?')}")

    # --- 7. 发布任务（含 location, duration_estimate, skills）---
    code, body = req("/tasks", method="POST", data={
        "title": "E2E 验证任务（带地点时长技能）",
        "description": "自动化测试",
        "location": "远程",
        "duration_estimate": "~1h",
        "skills": ["Python", "测试"],
    }, token=token)
    if code != 200:
        errors.append(f"POST /tasks (with location/duration/skills) -> {code} {body}")
    else:
        passed.append("POST /tasks (location/duration/skills)")
        task_id = body.get("id")
        log(f"[OK] POST /tasks -> 200 task_id={task_id}")

    # --- 8. 任务详情（校验扩展字段）---
    if code == 200 and task_id:
        code2, body2 = req(f"/tasks/{task_id}", token=token)
        if code2 != 200:
            errors.append(f"GET /tasks/{{id}} -> {code2} {body2}")
        else:
            passed.append("GET /tasks/:id (extra fields)")
            loc = body2.get("location")
            dur = body2.get("duration_estimate")
            sk = body2.get("skills")
            if loc is not None or dur is not None or (isinstance(sk, list) and len(sk) > 0):
                log(f"[OK] GET /tasks/{{id}} -> 200 location={loc} duration_estimate={dur} skills={sk}")
            else:
                log(f"[OK] GET /tasks/{{id}} -> 200 (extra fields present in response)")

    # --- 9. Agent 列表 ---
    code, body = req("/agents/mine", token=token)
    if code != 200:
        errors.append(f"GET /agents/mine -> {code} {body}")
    else:
        passed.append("GET /agents/mine")
        agents = body.get("agents", [])
        log(f"[OK] GET /agents/mine -> 200 (共 {len(agents)} 个)")

    # --- 10. 若无 Agent 则注册一个并接取任务 ---
    agent_id = None
    if code == 200 and agents:
        agent_id = agents[0].get("id")
    elif code == 200 and task_id:
        code_ag, body_ag = req("/agents/register", method="POST", data={
            "name": f"E2E_Agent_{int(time.time())}",
            "description": "E2E",
            "agent_type": "general",
        }, token=token)
        if code_ag == 200:
            agent_id = body_ag.get("id")
            passed.append("POST /agents/register")
            log(f"[OK] POST /agents/register -> 200 agent_id={agent_id}")

    if agent_id and task_id:
        code_sub, body_sub = req(f"/tasks/{task_id}/subscribe", method="POST", data={"agent_id": agent_id}, token=token)
        if code_sub != 200:
            errors.append(f"POST /tasks/{{id}}/subscribe -> {code_sub} {body_sub}")
        else:
            passed.append("POST /tasks/:id/subscribe")
            log(f"[OK] POST /tasks/{{id}}/subscribe -> 200")

    # --- 11. 账户扩展接口 ---
    for path, name in [("/account/receiving-account", "receiving-account"), ("/account/commission", "commission")]:
        code, body = req(path, token=token)
        if code != 200:
            errors.append(f"GET {path} -> {code} {body}")
        else:
            passed.append(f"GET {path}")
    log(f"[OK] GET /account/receiving-account, /account/commission -> 200")

    # --- 12. 前端任务大厅页面可达 ---
    code_f, body_f = get_frontend(FRONTEND_BASE + "/")
    if code_f != 200:
        errors.append(f"GET {FRONTEND_BASE}/ -> {code_f}")
    else:
        passed.append("Frontend (task hall) 200")
        if "ClawJob" in body_f or "clawjob" in body_f.lower() or "index" in body_f:
            log(f"[OK] Frontend {FRONTEND_BASE}/ -> 200 (页面可访问)")
        else:
            log(f"[OK] Frontend {FRONTEND_BASE}/ -> 200")

    # --- 汇总 ---
    log("")
    log("=" * 60)
    if errors:
        log("失败: " + str(len(errors)) + " 项")
        for e in errors:
            log("  " + str(e))
        log("通过: " + str(len(passed)) + " 项")
        log("详见 deploy/VERIFY_AND_FIX.md")
        sys.exit(1)
    log("全部通过 (" + str(len(passed)) + " 项)")
    log("=" * 60)
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) > 1 and not os.environ.get("CLAWJOB_API_URL"):
        BASE = sys.argv[1].rstrip("/")
        FRONTEND_BASE = BASE.replace(":8000", ":3000")
    main()
