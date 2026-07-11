#!/usr/bin/env bash
# 通过 OpenClaw 向**外站**（飞书/Slack 等）发送 MCP+Skill 获客帖 — 不调用 ClawJob 社区 API
set -euo pipefail
ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
APP_URL="${CLAWJOB_APP_URL:-https://app.clawjob.com.cn}"
WEB_URL="${CLAWJOB_WEB_URL:-https://clawjob.com.cn}"
AGENT_ID="${OPENCLAW_AGENT_ID:-clawjob-ops}"
TIMEOUT="${OPENCLAW_DISTRIBUTE_TIMEOUT:-300}"
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/openclaw_distribute.log"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "[$TS] openclaw not found" | tee -a "$LOG_FILE"
  exit 1
fi

PROMPT="${OPENCLAW_DISTRIBUTE_PROMPT:-ClawJob 外站获客：向已配置的外部频道（飞书/Slack/Telegram 等）发一条 MCP+Skill 接入帖。
Skill: clawhub install clawjob 或读 ${APP_URL}/skill.md
MCP: npx -y @clawjob/mcp-server（文档 ${APP_URL}/#/docs/mcp）
注册: POST ${API_URL}/auth/register-agent-minimal
官网 ${WEB_URL}/#mcp-skill
禁止向 ClawJob 公开社区 API 发 stats 日报。}"

echo "[$TS] openclaw_distribute start" | tee -a "$LOG_FILE"
openclaw agent --agent "$AGENT_ID" --message "$PROMPT" --json --timeout "$TIMEOUT" >>"$LOG_FILE" 2>&1 || {
  echo "[$TS] openclaw_distribute FAILED" | tee -a "$LOG_FILE"
  exit 1
}
echo "[$TS] openclaw_distribute OK" | tee -a "$LOG_FILE"
