#!/usr/bin/env bash
# 通过本地 OpenClaw Gateway 触发 ClawJob 增长运营任务（精简版：社区分发 > 自刷任务）
# 依赖：openclaw CLI、Gateway 运行中（openclaw gateway status）
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT_DIR" || { echo "cannot cd to CLAWJOB_ROOT=$ROOT_DIR"; exit 1; }
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"

API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
API_URL="${API_URL%/}"
AGENT_ID="${OPENCLAW_AGENT_ID:-clawjob-ops}"
TIMEOUT="${OPENCLAW_MISSION_TIMEOUT:-420}"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
LOG_FILE="$LOG_DIR/openclaw_mission.log"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "[$TS] ERROR: openclaw CLI not found. Install: npm i -g openclaw && openclaw onboard" | tee -a "$LOG_FILE"
  exit 1
fi

if ! openclaw gateway status >/dev/null 2>&1; then
  echo "[$TS] ERROR: OpenClaw Gateway not reachable. Run: openclaw gateway start" | tee -a "$LOG_FILE"
  exit 1
fi

# 轻量探活（health/stats/growth）
if [[ "${CLAWJOB_OPS_SKIP_PRECHECK:-0}" != "1" ]]; then
  CLAWJOB_API_URL="$API_URL" "$ROOT_DIR/tools/community_ops/run_community_ops.sh" >> "$LOG_FILE" 2>&1 || true
fi

JOIN_URL="${CLAWJOB_JOIN_URL:-https://app.clawjob.com.cn/#/join}"
COMMUNITY_URL="${CLAWJOB_COMMUNITY_URL:-https://app.clawjob.com.cn/#/community}"

MISSION="${OPENCLAW_MISSION_PROMPT:-ClawJob 每日增长运营（$(date +%F)）— 按 docs/OPENCLAW_DAILY_OPS_PLAN.md v4 与 clawjob-ops skill：

【目标】200 公开 Agent；Agent 对 Agent 结算优先；**禁止**向 ClawJob 公开社区发帖运营日报。

Phase A（必做）：GET ${API_URL}/stats 记录 agents_count_public、tasks_completed、rewards_paid、200 进度；读 ${API_URL}/public/agent-opportunities.json 与 referral-program.json（优先 agent_direct 任务）。

Phase B（必做）：读 .clawjob-credentials.json（#103）；GET earnings-summary。

Phase C（默认跳过；每周最多 1 次）：agent_direct showcase 闭环演示（subscribe→submit→验收→payer-mark-paid→payee-confirm）。不要每日 Quest #174-176。Ops 不是发布方，勿代验收。

Phase D（必做 · 仅内部渠道）：将 Markdown 日报（真实 stats、agent_direct 闭环、${JOIN_URL}、高奖励任务、referral）发到 **飞书**（Bot 已入 ClawJob 相关群或运营 DM）。**禁止** POST ${API_URL}/community/topics/*/messages 发「每日增长运营日报」或 stats 表格；社区只接受用户/Agent 真实讨论与任务复盘。

Phase E（必做）：记录 referral 分享动作；Moltbook 由独立 cron，勿 spam。

Phase F：返回 Markdown 摘要（stats、飞书结果、阻塞、下一步；community_post=skipped）。

约束：禁止 fake registration；禁止无真实交付 submit；stats 必须来自当次 API；禁止对外主推平台管理员提现叙事。}"

echo "[$TS] openclaw_mission start agent=$AGENT_ID api=$API_URL (agent-direct-settlement v3)" | tee -a "$LOG_FILE"

OUT="$(mktemp)"
if openclaw agent --agent "$AGENT_ID" --message "$MISSION" --json --timeout "$TIMEOUT" >"$OUT" 2>&1; then
  echo "[$TS] openclaw_mission OK" | tee -a "$LOG_FILE"
  cat "$OUT" >> "$LOG_FILE"
  if command -v jq >/dev/null 2>&1; then
    jq -r '.result.meta.finalAssistantVisibleText // .result.payloads[0].text // .summary // .' "$OUT" 2>/dev/null || cat "$OUT"
  else
    cat "$OUT"
  fi
else
  echo "[$TS] openclaw_mission FAILED" | tee -a "$LOG_FILE"
  cat "$OUT" | tee -a "$LOG_FILE"
  rm -f "$OUT"
  exit 1
fi
rm -f "$OUT"
