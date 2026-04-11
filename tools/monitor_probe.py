#!/usr/bin/env python3
"""
线上最小监控探针：
- 可用性：关键接口必须 2xx/3xx，且响应 JSON 结构符合预期
- 延迟：关键接口耗时不得超过阈值（默认 2500ms）

用法:
  python3 tools/monitor_probe.py
  CLAWJOB_API_URL=https://api.clawjob.com.cn python3 tools/monitor_probe.py
  CLAWJOB_MONITOR_MAX_MS=2000 python3 tools/monitor_probe.py
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

API = os.environ.get("CLAWJOB_API_URL", "https://api.clawjob.com.cn").rstrip("/")
MAX_MS = int(os.environ.get("CLAWJOB_MONITOR_MAX_MS", "2500"))


def request_json(path: str) -> tuple[int, dict, float]:
    url = f"{API}{path}"
    req = urllib.request.Request(url, method="GET")
    start = time.perf_counter()
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        ms = (time.perf_counter() - start) * 1000
        return resp.status, body, ms


def assert_ok(path: str, check_fn) -> float:
    status, body, ms = request_json(path)
    if status >= 500:
        raise RuntimeError(f"{path} 出现 5xx: {status}")
    if status >= 400:
        raise RuntimeError(f"{path} 返回错误状态码: {status}")
    if ms > MAX_MS:
        raise RuntimeError(f"{path} 延迟超阈值: {ms:.1f}ms > {MAX_MS}ms")
    check_fn(body)
    print(f"OK {path:<24} status={status} latency={ms:.1f}ms")
    return ms


def main() -> int:
    print(f"Probe API: {API} (max {MAX_MS}ms)")
    try:
        latencies = []
        latencies.append(
            assert_ok(
                "/health",
                lambda b: (
                    b.get("status") == "healthy"
                    and b.get("service") == "clawjob-backend"
                )
                or (_ for _ in ()).throw(RuntimeError("/health 结构不符合预期")),
            )
        )
        latencies.append(
            assert_ok(
                "/stats",
                lambda b: "tasks_count" in b
                or (_ for _ in ()).throw(RuntimeError("/stats 缺少 tasks_count")),
            )
        )
        latencies.append(
            assert_ok(
                "/stats/roi-series?days=14",
                lambda b: (
                    isinstance(b.get("series"), list)
                    and int(b.get("days") or 0) >= 7
                    and len(b.get("series") or []) == int(b.get("days") or 0)
                )
                or (_ for _ in ()).throw(RuntimeError("/stats/roi-series 数据不符合预期")),
            )
        )
    except urllib.error.URLError as e:
        print(f"网络错误: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Probe 失败: {e}", file=sys.stderr)
        return 1

    avg = sum(latencies) / len(latencies)
    print(f"Probe 通过: {len(latencies)} endpoints, avg={avg:.1f}ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
