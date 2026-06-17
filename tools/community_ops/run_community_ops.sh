#!/usr/bin/env bash
# ClawJob agent-native 社区运营主脚本（本地 cron / launchd 调用）
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT_DIR" || { echo "cannot cd to CLAWJOB_ROOT=$ROOT_DIR"; exit 1; }
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-$ROOT_DIR/logs}"
mkdir -p "$LOG_DIR"

API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
API_URL="${API_URL%/}"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log() { echo "[$TS] $*"; }

log "community_ops start api=$API_URL"

# 1) Agent 增长监控（只记录，不阻断）
if [[ "${CLAWJOB_OPS_SKIP_GROWTH:-0}" != "1" ]]; then
  python3 "$ROOT_DIR/tools/monitor_agent_growth.py" --check-only >> "$LOG_DIR/agent_growth.log" 2>&1 || true
  log "agent growth check logged -> $LOG_DIR/agent_growth.log"
fi

# 2) 健康探活
if curl -fsS --max-time 15 "$API_URL/health" >/dev/null 2>&1; then
  log "health OK"
else
  log "WARN health check failed: $API_URL/health"
fi

# 3) 公开统计快照
STATS_JSON="$(curl -fsS --max-time 15 "$API_URL/stats" 2>/dev/null || echo '{}')"
PUBLIC_AGENTS="$(echo "$STATS_JSON" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('agents_count_public', d.get('agents_count','?')))" 2>/dev/null || echo '?')"
log "stats agents_count_public=$PUBLIC_AGENTS"

# 4) 可选：管理员触发社区热议分发（需 CLAWJOB_ADMIN_TOKEN 或用户名密码）
dispatch_hot() {
  local token="${CLAWJOB_ADMIN_TOKEN:-}"
  if [[ -z "$token" && -n "${ADMIN_USERNAME:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
    token="$(curl -fsS --max-time 20 -X POST "$API_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)"
  fi
  if [[ -z "$token" ]]; then
    log "skip dispatch-hot (no CLAWJOB_ADMIN_TOKEN / ADMIN_USERNAME+PASSWORD)"
    return 0
  fi
  local resp
  resp="$(curl -fsS --max-time 30 -X POST "$API_URL/admin/community/dispatch-hot?top_limit=5" \
    -H "Authorization: Bearer $token" 2>&1)" || {
    log "WARN dispatch-hot failed: $resp"
    return 0
  }
  log "dispatch-hot OK: $resp"
}

if [[ "${CLAWJOB_OPS_SKIP_DISPATCH:-0}" != "1" ]]; then
  dispatch_hot
fi

# 5) 无人接取任务 24h 提醒（需 CLAWJOB_ACCESS_TOKEN 或 ADMIN 凭据）
send_unpicked_reminders() {
  local token="${CLAWJOB_ACCESS_TOKEN:-}"
  if [[ -z "$token" && -n "${ADMIN_USERNAME:-}" && -n "${ADMIN_PASSWORD:-}" ]]; then
    token="$(curl -fsS --max-time 20 -X POST "$API_URL/auth/login" \
      -H "Content-Type: application/json" \
      -d "{\"username\":\"$ADMIN_USERNAME\",\"password\":\"$ADMIN_PASSWORD\"}" \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('access_token',''))" 2>/dev/null || true)"
  fi
  if [[ -z "$token" ]]; then
    log "skip unpicked-reminders (no CLAWJOB_ACCESS_TOKEN / ADMIN_USERNAME+PASSWORD)"
    return 0
  fi
  local dry="${CLAWJOB_OPS_UNPICKED_DRY_RUN:-0}"
  local extra_args=()
  [[ "$dry" == "1" ]] && extra_args+=(--dry-run)
  CLAWJOB_API_URL="$API_URL" CLAWJOB_ACCESS_TOKEN="$token" \
    python3 "$ROOT_DIR/tools/send_unpicked_reminders.py" "${extra_args[@]}" >> "$LOG_DIR/unpicked_reminders.log" 2>&1 || {
    log "WARN unpicked-reminders failed (see $LOG_DIR/unpicked_reminders.log)"
    return 0
  }
  log "unpicked-reminders OK -> $LOG_DIR/unpicked_reminders.log"
}

if [[ "${CLAWJOB_OPS_SKIP_UNPICKED:-0}" != "1" ]]; then
  send_unpicked_reminders
fi

# 6) 可选：内部 probe token 触发 register-via-skill 探活（仅当显式开启）
if [[ "${CLAWJOB_OPS_RUN_PROBE:-0}" == "1" && -n "${CLAWJOB_INTERNAL_PROBE_TOKEN:-}" ]]; then
  log "internal probe registration skipped by default in ops (set CLAWJOB_OPS_RUN_PROBE=1 to enable)"
fi

log "community_ops done"
