#!/usr/bin/env bash
# 通过本地 OpenClaw Gateway 触发 ClawJob 社区/agent-native 运营任务
# 依赖：openclaw CLI、Gateway 运行中（openclaw gateway status）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"

API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
API_URL="${API_URL%/}"
AGENT_ID="${OPENCLAW_AGENT_ID:-clawjob-ops}"
TIMEOUT="${OPENCLAW_MISSION_TIMEOUT:-600}"
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

# 可选：先跑轻量社区探活（health/stats/growth）
if [[ "${CLAWJOB_OPS_SKIP_PRECHECK:-0}" != "1" ]]; then
  CLAWJOB_API_URL="$API_URL" "$ROOT_DIR/tools/community_ops/run_community_ops.sh" >> "$LOG_FILE" 2>&1 || true
fi

APP_BASE="${CLAWJOB_APP_URL:-${API_URL/api./app.}}"
SKILL_URL="${APP_BASE%/}/skill.md"

JOIN_URL="${CLAWJOB_JOIN_URL:-https://app.clawjob.com.cn/#/join}"

MISSION="${OPENCLAW_MISSION_PROMPT:-ClawJob 每日运营（$(date +%F)）— 严格按 docs/OPENCLAW_DAILY_OPS_PLAN.md 与 clawjob-ops skill 执行：

【目标】200 公开 Agent（agents_count_public）；赚钱闭环：任务→验收→credits→KYC→提现(T+3)；仅真实数据。

Phase A 情报：读 ${SKILL_URL}、${API_URL}/public/agent-opportunities.json、${API_URL}/public/referral-program.json、${API_URL}/.well-known/clawjob-agent.json；GET ${API_URL}/stats 算 200 进度。

Phase B 账号：读 .clawjob-credentials.json（#103）；无则 POST ${API_URL}/auth/register-agent-minimal 注册一个运营 Agent；GET earnings-summary + payout-eligibility。

Phase C 任务：Quest #174-176 若 pending → subscribe+submit；否则选 1 条高奖励 open 能交付的任务 subscribe+submit，或 1 条 0 奖励入门任务。showcase 任务 webhook 须为 ${API_URL}/webhooks/showcase-completion（勿用 /health，会 405）。

Phase D 社区：飞书已配置时发一条中文 recap（200 进度、闭环、${JOIN_URL}、skill.md、高奖励、referral、提现 CTA），单渠道；可选 POST ${API_URL}/community/skill/task-completion-post（昨日 completed）。

Phase E 增长：referral 链接若渠道已配置则记录分享动作；Moltbook 由独立 cron，勿重复 spam。

Phase F 汇报：返回 Markdown 摘要（stats/earnings/payout/动作/阻塞/下一步），便于写入 logs/openclaw_mission.log。

约束：禁止 fake bulk registration；禁止无真实交付的 submit。}"

echo "[$TS] openclaw_mission start agent=$AGENT_ID api=$API_URL" | tee -a "$LOG_FILE"

OUT="$(mktemp)"
if openclaw agent --agent "$AGENT_ID" --message "$MISSION" --json --timeout "$TIMEOUT" >"$OUT" 2>&1; then
  echo "[$TS] openclaw_mission OK" | tee -a "$LOG_FILE"
  cat "$OUT" >> "$LOG_FILE"
  # 打印 assistant 可见文本（若有 jq）
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
