#!/usr/bin/env bash
# 对当前线上（或 CLAWJOB_API_URL / PLAYWRIGHT_BASE_URL 指定环境）跑公开 API 冒烟 + 监控探针 + Playwright 站点冒烟。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
API="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
WEB="${PLAYWRIGHT_BASE_URL:-https://clawjob.com.cn}"
echo "[production-e2e] API: ${API}"
echo "[production-e2e] Web: ${WEB}"
CLAWJOB_API_URL="${API}" python3 tools/verify_online_e2e.py
CLAWJOB_API_URL="${API}" python3 tools/monitor_probe.py
(
  cd "${ROOT}/frontend"
  PLAYWRIGHT_BASE_URL="${WEB}" npm run e2e
)
echo "[production-e2e] 全部通过。"
