#!/usr/bin/env bash
# ClawJob 自动拉新：种子保底 + 社区/MCP 分发（+ 可选 OpenClaw）
# 用法：
#   ./tools/growth/run_daily_acquisition.sh           # 完整 daily
#   ./tools/growth/run_daily_acquisition.sh --pulse    # 6h 脉冲（跳过 openclaw mission）
#   ./tools/growth/run_daily_acquisition.sh --dry-run  # 不发帖、不写种子 apply 外的副作用（种子仍可 dry）
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT_DIR" || { echo "cannot cd to CLAWJOB_ROOT=$ROOT_DIR"; exit 1; }

MODE="daily"
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --pulse) MODE="pulse" ;;
    --dry-run) DRY_RUN=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
      exit 0
      ;;
  esac
done

API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
API_URL="${API_URL%/}"
APP_URL="${CLAWJOB_APP_URL:-https://app.clawjob.com.cn}"
WEB_URL="${CLAWJOB_WEB_URL:-https://clawjob.com.cn}"
COMPOSE_DIR="${CLAWJOB_COMPOSE_DIR:-$ROOT_DIR/deploy}"
COMPOSE_FILE="${CLAWJOB_COMPOSE_FILE:-docker-compose.prod.yml}"
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-/var/log/clawjob}"
STATE_FILE="$ROOT_DIR/tools/growth/.distribution_state.json"
PAUSE_FILE="$ROOT_DIR/tools/growth/.acquisition_paused"
MIN_AGENT_DIRECT="${MIN_AGENT_DIRECT_OPEN:-3}"
CHANNELS_DAILY="${DISTRIBUTION_CHANNELS:-community,mcp-market}"
CHANNELS_PULSE="${DISTRIBUTION_CHANNELS_PULSE:-community,mcp-market}"
SKIP_OPENCLAW="${SKIP_OPENCLAW_EXTERNAL:-1}"

mkdir -p "$LOG_DIR" "$ROOT_DIR/logs" "$(dirname "$STATE_FILE")"
if [[ ! -w "$LOG_DIR" ]]; then
  LOG_DIR="$ROOT_DIR/logs"
  mkdir -p "$LOG_DIR"
fi

LOG_FILE="$LOG_DIR/acquisition-${MODE}.log"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

log() { echo "[$TS] $*"; echo "[$TS] $*" >>"$LOG_FILE"; }

if [[ -f "$PAUSE_FILE" ]]; then
  log "PAUSED: found $PAUSE_FILE — exit 0"
  exit 0
fi

log "=== acquisition start mode=$MODE dry_run=$DRY_RUN api=$API_URL root=$ROOT_DIR ==="

# --- 1) Health ---
if ! curl -fsS --max-time 20 "$API_URL/health" >/dev/null 2>&1; then
  log "ERROR: health failed $API_URL/health"
  exit 2
fi
log "health OK"

# --- 2) Seed via docker (idempotent) ---
docker_seed() {
  local script="$1"
  local label="$2"
  if [[ ! -f "$COMPOSE_DIR/$COMPOSE_FILE" ]]; then
    log "WARN: compose file missing $COMPOSE_DIR/$COMPOSE_FILE — skip $label"
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    log "WARN: docker not found — skip $label"
    return 0
  fi
  local apply_flag="--apply"
  if [[ "$DRY_RUN" == "1" ]]; then
    apply_flag=""
    log "dry-run: would seed $label (preview only)"
  fi
  if (
    cd "$COMPOSE_DIR"
    docker compose -f "$COMPOSE_FILE" exec -T backend \
      sh -c "cd /app && PYTHONPATH=. python3 scripts/${script} ${apply_flag}"
  ) >>"$LOG_FILE" 2>&1; then
    log "seed OK: $label"
  else
    log "WARN: seed failed: $label (see log)"
  fi
}

docker_seed "seed_onboarding_quest.py" "onboarding_quest"
docker_seed "seed_open_tasks.py" "open_tasks+agent_direct"

# --- 3) Verify supply (best-effort via public APIs) ---
verify_supply() {
  local oq_json stats_json
  oq_json="$(curl -fsS --max-time 20 "$API_URL/.well-known/clawjob-agent.json" 2>/dev/null || echo '{}')"
  stats_json="$(curl -fsS --max-time 20 "$API_URL/stats" 2>/dev/null || echo '{}')"
  python3 - "$oq_json" "$stats_json" "$MIN_AGENT_DIRECT" <<'PY' >>"$LOG_FILE" 2>&1 || true
import json, sys
oq = json.loads(sys.argv[1] or "{}")
stats = json.loads(sys.argv[2] or "{}")
need = int(sys.argv[3])
quest = oq.get("onboarding_quest") or {}
count = int(quest.get("count") or 0)
print(f"onboarding_quest.count={count} ids={quest.get('ids') or oq.get('onboarding_quest_ids')}")
print(f"stats agents_count_public={stats.get('agents_count_public')} tasks_open={stats.get('tasks_open')} tasks_completed={stats.get('tasks_completed')}")
if count < 3:
    print(f"WARN: onboarding_quest.count={count} < 3")
print(f"target MIN_AGENT_DIRECT_OPEN={need} (enforced by seed_open_tasks showcase set)")
PY
  log "supply check logged"
}
verify_supply

# --- 4) Distribution ---
CHANNELS="$CHANNELS_DAILY"
[[ "$MODE" == "pulse" ]] && CHANNELS="$CHANNELS_PULSE"
# Default: do not require openclaw on server; opt-in via SKIP_OPENCLAW_EXTERNAL=0 + channel list
if [[ "$SKIP_OPENCLAW" != "1" ]]; then
  case ",$CHANNELS," in
    *,openclaw,*) ;;
    *) CHANNELS="${CHANNELS},openclaw" ;;
  esac
fi

DIST_ARGS=(--channels "$CHANNELS")
[[ "$DRY_RUN" == "1" ]] && DIST_ARGS+=(--dry-run)

export CLAWJOB_API_URL="$API_URL"
export CLAWJOB_APP_URL="$APP_URL"
export CLAWJOB_WEB_URL="$WEB_URL"
export SKIP_OPENCLAW_EXTERNAL="$SKIP_OPENCLAW"

log "distribute channels=$CHANNELS"
if python3 "$ROOT_DIR/tools/growth/distribute_agent_onboarding.py" "${DIST_ARGS[@]}" >>"$LOG_FILE" 2>&1; then
  log "distribute OK"
else
  log "WARN: distribute exited non-zero (see log)"
fi

# --- 5) Optional OpenClaw daily mission (Feishu recap) — daily only ---
if [[ "$MODE" == "daily" && "$DRY_RUN" != "1" ]]; then
  if command -v openclaw >/dev/null 2>&1; then
    if [[ -x "$ROOT_DIR/tools/community_ops/openclaw_mission.sh" ]]; then
      log "openclaw_mission start"
      CLAWJOB_ROOT="$ROOT_DIR" CLAWJOB_API_URL="$API_URL" CLAWJOB_OPS_LOG_DIR="$LOG_DIR" \
        "$ROOT_DIR/tools/community_ops/openclaw_mission.sh" >>"$LOG_FILE" 2>&1 || log "WARN: openclaw_mission failed"
    fi
  else
    log "skip openclaw_mission (CLI not installed on server — Feishu recap blocked)"
  fi
elif [[ "$MODE" == "daily" && "$DRY_RUN" == "1" ]]; then
  log "dry-run: skip openclaw_mission"
fi

# --- 6) Milestone + state touch ---
CLAWJOB_API_URL="$API_URL" "$ROOT_DIR/tools/growth/check_milestone.sh" >>"$LOG_FILE" 2>&1 || true

# Ensure state file exists even if distribute was dry-run
if [[ ! -f "$STATE_FILE" ]]; then
  echo "{\"topics\":{},\"mcp_published\":false,\"last_run\":null}" >"$STATE_FILE"
fi
python3 - "$STATE_FILE" "$MODE" "$DRY_RUN" <<'PY' || true
import json, sys
from datetime import datetime, timezone
path, mode, dry = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    st = json.loads(open(path, encoding="utf-8").read())
except Exception:
    st = {"topics": {}, "mcp_published": False}
st["last_acquisition_mode"] = mode
st["last_acquisition_at"] = datetime.now(timezone.utc).isoformat()
st["last_dry_run"] = dry == "1"
open(path, "w", encoding="utf-8").write(json.dumps(st, indent=2, ensure_ascii=False) + "\n")
print(f"state updated {path}")
PY

log "=== acquisition done mode=$MODE ==="
exit 0
