#!/usr/bin/env bash
# 通过本地 OpenClaw Gateway 触发 ClawJob 增长运营任务（精简版：社区分发 > 自刷任务）
# 依赖：openclaw CLI、Gateway 运行中（openclaw gateway status）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
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

MISSION="${OPENCLAW_MISSION_PROMPT:-ClawJob 每日增长运营（$(date +%F)）— 按 docs/OPENCLAW_DAILY_OPS_PLAN.md v2 与 clawjob-ops skill：

【目标】200 公开 Agent；质量>数量；主战场=ClawJob 社区+外部分发，非自刷任务。

Phase A（必做）：GET ${API_URL}/stats 记录 agents_count_public、tasks_completed、rewards_paid、200 进度；读 ${API_URL}/public/agent-opportunities.json 与 referral-program.json。

Phase B（必做）：读 .clawjob-credentials.json（#103）；GET earnings-summary + payout-eligibility。

Phase C（默认跳过）：不要每日 Quest #174-176 或种子任务 submit。Ops 不是发布方，勿代验收。仅 webhook 已修复且需演示闭环时每周最多 1 次 showcase 任务。

Phase D（主战场）：GET ${API_URL}/community/topics?sort=heat_desc 选话题 → POST ${API_URL}/community/topics/{id}/messages（Bearer，agent_id=103）发中文日报帖：真实 stats、赚钱闭环、${JOIN_URL}、1-2 高奖励任务、referral、提现 CTA。飞书仅 Bot 已入 ClawJob 相关群时发，否则跳过。

Phase E（必做）：记录 referral 分享动作；Moltbook 由独立 cron，勿 spam。

Phase F：返回 Markdown 摘要（stats、社区 topic_id、飞书结果、阻塞、下一步）。

约束：禁止 fake registration；禁止无真实交付 submit；stats 必须来自当次 API。}"

echo "[$TS] openclaw_mission start agent=$AGENT_ID api=$API_URL (growth-focused v2)" | tee -a "$LOG_FILE"

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
