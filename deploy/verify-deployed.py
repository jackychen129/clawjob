#!/usr/bin/env python3
"""验证已部署的 ClawJob API 与关键流程。用法: python3 deploy/verify-deployed.py [BASE_URL]"""
import os
import sys
import json
import time

# NOTE: translated comment in English.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "verify-result.txt")

def log(msg):
    print(msg)
    sys.stdout.flush()
    try:
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

def suggest_fixes(errors):
    """根据错误类型给出常见修复建议"""
    lines = []
    for e in errors:
        es = str(e)
        if "timed out" in es or "timeout" in es.lower():
            lines.append("• 请求超时：1) 在服务器上执行 bash /opt/clawjob/deploy/verify-on-server.sh 做本机诊断；2) 检查云厂商防火墙是否放行 80/3000/8000；3) 确认容器在运行：docker ps")
            break
    for e in errors:
        es = str(e)
        if "500" in es:
            lines.append("• 5xx 错误：常见为数据库未初始化。在服务器上执行：cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\"'")
            break
    for e in errors:
        es = str(e)
        if "CORS" in es or "403" in es or "Origin" in es:
            lines.append("• CORS/403：在 deploy/.env 中设置 CORS_ORIGINS 为前端地址，如 http://43.99.97.240:3000 或你的域名，重启 backend 容器")
            break
    for e in errors:
        es = str(e)
        if "401" in es or "422" in es:
            lines.append("• 401/422：检查注册/登录请求体格式；JWT_SECRET 需与部署环境一致且非默认值")
            break
    if lines:
        log("\n--- 常见修复建议 ---")
        for line in lines:
            log(line)
        log("详见 deploy/README_DEPLOY_ALL.md 与 deploy/VERIFY_AND_FIX.md")

try:
    import urllib.request
    import urllib.error
    import ssl
except ImportError:
    print("Python 3 required")
    sys.exit(1)

BASE = os.environ.get("CLAWJOB_API_URL", "http://43.99.97.240:8000").rstrip("/")
INTERNAL_PROBE_TOKEN = os.environ.get("CLAWJOB_INTERNAL_PROBE_TOKEN", "").strip()
SSL_CTX = ssl.create_default_context()

def req(path, method="GET", data=None, token=None):
    url = f"{BASE}{path}"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=25, context=SSL_CTX) as res:
            return res.getcode(), json.loads(res.read().decode())
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()
            return e.code, json.loads(body) if body.strip().startswith("{") else {"detail": body}
        except Exception:
            return e.code, {"detail": str(e)}
    except Exception as e:
        return 0, {"detail": str(e), "error_type": type(e).__name__}

def main():
    # NOTE: translated comment in English.
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(f"验证时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    except Exception:
        pass

    log(f"API Base: {BASE}\n")
    errors = []

    # 1. Health
    code, body = req("/health")
    if code != 200:
        errors.append(f"GET /health -> {code} {body}")
    else:
        log(f"[OK] GET /health -> {code} {body.get('status', body)}")

    # 2. Tasks list (public)
    code, body = req("/tasks")
    if code != 200:
        errors.append(f"GET /tasks -> {code} {body}")
    else:
        tasks = body.get("tasks", [])
        log(f"[OK] GET /tasks -> {code} (tasks: {len(tasks)})")

    # 2b. Candidates (public)
    code, body = req("/candidates")
    if code != 200:
        errors.append(f"GET /candidates -> {code} {body}")
    else:
        cands = body.get("candidates", [])
        log(f"[OK] GET /candidates -> {code} (candidates: {len(cands)})")

    # NOTE: translated comment in English.
    user = f"verify_{int(time.time())}"
    # NOTE: register-via-skill 的第二条任务会进入公开大厅。为了不污染线上任务列表，
    # 这里使用 `_internal=True` 内部标记让平台落库后直接隐藏；同时仍然按 SKILL.md
    # 模板填写正文，以便校验加强后的校验逻辑（真实 Skill 生成）仍能通过。
    payload = {
        "agent_name": f"DeployProbe_{user}",
        "description": "部署健康检查专用账号，非真实 Agent，完成验证后即废弃。",
        "agent_type": "general",
        "second_task": {
            "title": "[internal] deploy health probe (do not pick up)",
            "description": (
                "Context: Internal deploy health probe only; verifies register-via-skill "
                "persistence without public pickup intent.\n"
                "Deliverables: Agent row, hidden second task row, JWT in response.\n"
                "Acceptance criteria: HTTP 200, access_token present, task not in public hall.\n"
                "Constraints: _internal probe token; reward 0; do not subscribe in production.\n"
                "Time estimate: 5 minutes automated check."
            ),
            "task_type": "general",
            "priority": "low",
            "reward_points": 0,
            "category": "other",
        },
    }
    if INTERNAL_PROBE_TOKEN:
        payload["internal_probe_token"] = INTERNAL_PROBE_TOKEN
    code, body = req("/auth/register-via-skill", method="POST", data=payload)
    token = None
    if code != 200:
        errors.append(f"POST /auth/register-via-skill -> {code} {body}")
    else:
        token = body.get("access_token")
        log(f"[OK] POST /auth/register-via-skill -> {code} username={body.get('username', user)}")

    if not token:
        log("\n[SKIP] 后续需要 token，跳过发布/Agent 等校验")
        if errors:
            log("\nErrors: " + str(errors))
            suggest_fixes(errors)
            sys.exit(1)
        return

    # 4. Me / balance
    code, body = req("/account/me", token=token)
    if code != 200:
        errors.append(f"GET /account/me -> {code} {body}")
    else:
        log(f"[OK] GET /account/me -> {code} credits={body.get('credits', '?')}")

    # 5. Publish task path is already exercised by register-via-skill above
    #    (creates handshake + second_task). 额外再 POST /tasks 会在线上大厅留下
    #    测试任务，因此改为只做轻量探测：验证接口可达但不写入多余数据。
    code, body = req("/tasks?limit=1", token=token)
    if code != 200:
        errors.append(f"GET /tasks (auth probe) -> {code} {body}")
    else:
        log(f"[OK] GET /tasks (auth probe) -> {code} tasks={len(body.get('tasks', []))}")

    # 6. Agents list
    code, body = req("/agents/mine", token=token)
    if code != 200:
        errors.append(f"GET /agents/mine -> {code} {body}")
    else:
        agents = body.get("agents", [])
        log(f"[OK] GET /agents/mine -> {code} agents={len(agents)}")

    # 7. Receiving account & commission
    code, body = req("/account/receiving-account", token=token)
    if code != 200:
        errors.append(f"GET /account/receiving-account -> {code} {body}")
    else:
        log(f"[OK] GET /account/receiving-account -> {code}")
    code, body = req("/account/commission", token=token)
    if code != 200:
        errors.append(f"GET /account/commission -> {code} {body}")
    else:
        log(f"[OK] GET /account/commission -> {code} balance={body.get('commission_balance', '?')}")

    log("")
    if errors:
        log("Errors: " + str(errors))
        suggest_fixes(errors)
        sys.exit(1)
    log("All checks passed.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        BASE = sys.argv[1].rstrip("/")
    main()
