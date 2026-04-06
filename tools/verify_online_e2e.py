#!/usr/bin/env python3
"""
线上 / 预发 API 冒烟与可选完整闭环 E2E。

公开检查（任意环境，默认对生产 API）：
  - GET /health（clawjob-backend）
  - GET /stats
  - GET /stats/roi-series?days=14

完整「注册 → 充值 → 发布 → 接取 → 验收」仅建议在**本地后端**执行（生产注册需邮箱验证码，
见 tools/e2e_publish_and_complete.py）。

用法:
  # 生产 API 冒烟（默认）
  python3 tools/verify_online_e2e.py

  # 指定 API
  CLAWJOB_API_URL=https://api.example.com python3 tools/verify_online_e2e.py

  # 本地同时跑 Python API 闭环（需本机 backend 已启动且无验证码限制）
  CLAWJOB_API_URL=http://localhost:8000 CLAWJOB_E2E_FULL=1 python3 tools/verify_online_e2e.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = os.environ.get("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
ROOT = Path(__file__).resolve().parent.parent
E2E_SCRIPT = ROOT / "tools" / "e2e_publish_and_complete.py"


def req_json(method: str, path: str) -> dict:
    url = f"{API}{path}"
    r = urllib.request.Request(url, method=method)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def run_public_smoke() -> None:
    print("检查 API:", API)
    health = req_json("GET", "/health")
    if health.get("status") != "healthy":
        raise RuntimeError(f"health 异常: {health}")
    if health.get("service") != "clawjob-backend":
        raise RuntimeError(f"非 ClawJob 后端: {health.get('service')}")
    print("  OK /health")

    stats = req_json("GET", "/stats")
    if "tasks_count" not in stats:
        raise RuntimeError(f"/stats 缺少 tasks_count: {stats}")
    print("  OK /stats")

    roi = req_json("GET", "/stats/roi-series?days=14")
    series = roi.get("series") or []
    days = int(roi.get("days") or 0)
    if days < 7 or len(series) != days:
        raise RuntimeError(f"/stats/roi-series 序列长度异常: days={days} len={len(series)}")
    print("  OK /stats/roi-series")

    print("公开冒烟通过。")


def should_run_full_e2e() -> bool:
    if os.environ.get("CLAWJOB_E2E_FULL") != "1":
        return False
    parsed = urllib.parse.urlparse(API)
    host = (parsed.hostname or "").lower()
    return host in ("localhost", "127.0.0.1") or host.startswith("127.")


def main() -> int:
    try:
        run_public_smoke()
    except urllib.error.URLError as e:
        print(f"网络错误: {e}", file=sys.stderr)
        return 4
    except Exception as e:
        print(f"冒烟失败: {e}", file=sys.stderr)
        return 1

    if should_run_full_e2e():
        if not E2E_SCRIPT.is_file():
            print("未找到 tools/e2e_publish_and_complete.py", file=sys.stderr)
            return 2
        print("CLAWJOB_E2E_FULL=1 且为本地 API，执行完整 API E2E …")
        env = {**os.environ, "CLAWJOB_API_URL": API}
        r = subprocess.run([sys.executable, str(E2E_SCRIPT)], cwd=str(ROOT), env=env)
        return r.returncode

    print(
        "提示: 完整注册类 E2E 未对生产默认执行（需邮箱验证码）。"
        "本地请: CLAWJOB_API_URL=http://localhost:8000 CLAWJOB_E2E_FULL=1 python3 tools/verify_online_e2e.py"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
