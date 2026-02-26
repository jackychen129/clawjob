#!/usr/bin/env python3
"""验证已部署的 ClawJob API 与关键流程。用法: python3 deploy/verify-deployed.py [BASE_URL]"""
import os
import sys
import json
import time

# 结果同时写入 deploy/verify-result.txt 便于查看
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
            lines.append("• 请求超时：请检查 1) 服务器防火墙是否放行 80/3000/8000；2) 后端容器是否运行：ssh 到服务器执行 docker ps")
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
    # 清空上次结果并写时间戳
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

    # 3. Register
    import time
    user = f"verify_{int(time.time())}"
    code, body = req("/auth/register", method="POST", data={
        "username": user,
        "email": f"{user}@test.local",
        "password": "verify-pass-123",
    })
    token = None
    if code != 200:
        errors.append(f"POST /auth/register -> {code} {body}")
    else:
        token = body.get("access_token")
        log(f"[OK] POST /auth/register -> {code} username={user}")

    if not token:
        log("\n[SKIP] 后续需要 token，跳过发布/Agent 等校验")
        if errors:
            log("\nErrors: " + str(errors))
            sys.exit(1)
        return

    # 4. Me / balance
    code, body = req("/account/me", token=token)
    if code != 200:
        errors.append(f"GET /account/me -> {code} {body}")
    else:
        log(f"[OK] GET /account/me -> {code} credits={body.get('credits', '?')}")

    # 5. Publish task (no reward)
    code, body = req("/tasks", method="POST", data={"title": "验证部署任务", "description": "自动验证"}, token=token)
    if code != 200:
        errors.append(f"POST /tasks -> {code} {body}")
    else:
        tid = body.get("id")
        log(f"[OK] POST /tasks -> {code} task_id={tid}")

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
