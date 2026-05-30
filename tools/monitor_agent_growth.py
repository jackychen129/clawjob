#!/usr/bin/env python3
"""
Agent 注册增长监控：读取本地 baseline，对比线上 /stats 与 /stats/recent-agents。

用法:
  python3 tools/monitor_agent_growth.py
  python3 tools/monitor_agent_growth.py --threshold 10
  python3 tools/monitor_agent_growth.py --check-only --threshold 10
  CLAWJOB_API_URL=https://api.clawjob.com.cn python3 tools/monitor_agent_growth.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = os.environ.get("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
BASELINE_PATH = Path(__file__).resolve().parent / "agent_growth_baseline.json"


def load_baseline() -> dict:
    if not BASELINE_PATH.is_file():
        raise FileNotFoundError(f"缺少 baseline 文件: {BASELINE_PATH}")
    with BASELINE_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def fetch_json(path: str) -> dict:
    url = f"{API}{path}"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return iso


def main() -> int:
    parser = argparse.ArgumentParser(description="监控 Agent 注册增长 vs baseline")
    parser.add_argument(
        "--threshold",
        type=int,
        default=10,
        help="自 baseline 起新增 Agent 数达到该值则 exit 0（默认 10）",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="精简输出，适合 cron/CI",
    )
    args = parser.parse_args()

    try:
        baseline = load_baseline()
        stats = fetch_json("/stats")
        recent = fetch_json("/stats/recent-agents")
    except urllib.error.URLError as e:
        print(f"网络错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        return 1

    baseline_count = int(baseline.get("baseline_agents_count", 0))
    current = int(stats.get("agents_count", 0))
    delta = current - baseline_count
    recent_7d = int(recent.get("recent_agents_7d", 0))
    milestone_next = int(baseline.get("milestone_next", baseline_count + 10))
    target = int(baseline.get("target", 500))
    remaining = max(0, milestone_next - current)
    target_remaining = max(0, target - current)
    threshold_met = delta >= args.threshold
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if args.check_only:
        status = "PASS" if threshold_met else "WAIT"
        print(
            f"{status} agents={current} baseline={baseline_count} "
            f"delta=+{delta} recent_7d={recent_7d} threshold={args.threshold}"
        )
    else:
        print(f"API: {API}")
        print(f"检查时间: {now}")
        print(f"Baseline: {baseline_count} agents @ {fmt_ts(baseline.get('baseline_at'))}")
        if baseline.get("note"):
            print(f"  说明: {baseline['note']}")
        print(f"当前:     {current} agents (Δ +{delta})")
        print(f"近 7 天:  {recent_7d} 新注册 (recent_agents_7d)")
        print()
        print("里程碑:")
        print(f"  +10 暂停迭代: {milestone_next} agents（还差 {remaining}）")
        print(f"  终极目标:     {target} agents（还差 {target_remaining}）")
        print()
        if threshold_met:
            print(f"✓ 已达 threshold +{args.threshold}（自 baseline 起新增 {delta}）")
        else:
            print(f"○ 未达 threshold +{args.threshold}（当前新增 {delta}，还需 {args.threshold - delta}）")
        if recent_7d >= 10:
            print("⚠ 近 7 天新注册 ≥ 10，建议暂停功能 sprint（见 docs/AGENT_GROWTH_RUNBOOK.md）")
        elif recent_7d < 3:
            print("ℹ 近 7 天新注册 < 3，增长偏慢")

    return 0 if threshold_met else 1


if __name__ == "__main__":
    sys.exit(main())
