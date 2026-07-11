#!/usr/bin/env bash
# 每周 Agent 获客分发（社区 + MCP 市场 + Skill 同步）
# crontab 示例：0 10 * * 1 cd /path/clawjob && CLAWJOB_API_URL=https://api.clawjob.com.cn ./tools/growth/run_agent_distribution.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export CLAWJOB_API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
export CLAWJOB_APP_URL="${CLAWJOB_APP_URL:-https://app.clawjob.com.cn}"
export CLAWJOB_WEB_URL="${CLAWJOB_WEB_URL:-https://clawjob.com.cn}"
LOG="${CLAWJOB_OPS_LOG_DIR:-$ROOT/logs}/agent_distribution.log"
mkdir -p "$(dirname "$LOG")"
{
  echo "=== $(date -u +"%Y-%m-%dT%H:%M:%SZ") agent distribution ==="
  python3 "$ROOT/tools/growth/distribute_agent_onboarding.py" \
    --channels "${DISTRIBUTION_CHANNELS:-community,mcp-market,skill-sync,openclaw}"
} >>"$LOG" 2>&1
echo "logged to $LOG"
