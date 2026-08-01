#!/usr/bin/env bash
# ClawJob 每日产品+运维优化循环（生产机 /opt/clawjob）
# 管道：Health → Metrics → Competitive → Safe apply → Ship queue → Deploy → Notify
#
# 用法：
#   ./tools/growth/run_daily_product_loop.sh              # 完整 daily
#   ./tools/growth/run_daily_product_loop.sh --weekly      # 周日加深竞品复盘
#   ./tools/growth/run_daily_product_loop.sh --skip-deploy # 跳过部署
#   ./tools/growth/run_daily_product_loop.sh --dry-run     # 只观测，不 apply / 不部署
#
# Pause: touch tools/growth/.daily_loop_paused
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
cd "$ROOT_DIR" || { echo "cannot cd CLAWJOB_ROOT=$ROOT_DIR"; exit 1; }

WEEKLY=0
DRY_RUN=0
SKIP_DEPLOY=0
for arg in "$@"; do
  case "$arg" in
    --weekly) WEEKLY=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --skip-deploy) SKIP_DEPLOY=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
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
PAUSE_FILE="$ROOT_DIR/tools/growth/.daily_loop_paused"
LOCK_FILE="${CLAWJOB_DAILY_LOCK:-/tmp/clawjob-daily-product-loop.lock}"
LAST_DEPLOY_SHA_FILE="$ROOT_DIR/tools/growth/.last_daily_deploy_sha"
MIRROR_DIR="${CLAWJOB_SRC_MIRROR:-$ROOT_DIR/.src-mirror}"
GIT_REMOTE="${CLAWJOB_GIT_REMOTE:-https://github.com/jackychen129/clawjob.git}"
GIT_BRANCH="${CLAWJOB_GIT_BRANCH:-main}"
FORCE_REBUILD_BACKEND="${FORCE_REBUILD_BACKEND:-0}"

mkdir -p "$LOG_DIR" "$ROOT_DIR/logs" "$ROOT_DIR/tools/growth" "$ROOT_DIR/docs" 2>/dev/null || true
if [[ ! -w "$LOG_DIR" ]]; then
  LOG_DIR="$ROOT_DIR/logs"
  mkdir -p "$LOG_DIR"
fi

DAY_LOCAL="$(TZ=Asia/Shanghai date +%Y%m%d)"
TS_UTC="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
TS_SH="$(TZ=Asia/Shanghai date +"%Y-%m-%d %H:%M:%S %Z")"
LOG_FILE="$LOG_DIR/daily-product-loop.log"
METRICS_FILE="$LOG_DIR/daily-metrics-${DAY_LOCAL}.json"
SUMMARY_FILE="$LOG_DIR/daily-product-summary-${DAY_LOCAL}.md"
COMP_DOC="$ROOT_DIR/docs/COMPETITIVE_DAILY.md"
QUEUE_DOC="$ROOT_DIR/docs/DAILY_OPTIMIZATION_QUEUE.md"

SUMMARY_LINES=()
DEPLOYED=0
DEPLOY_SHA=""
HEALTH_OK=0
HEALED=0

log() {
  echo "[$TS_UTC] $*"
  echo "[$TS_UTC] $*" >>"$LOG_FILE"
}

note() {
  SUMMARY_LINES+=("$*")
  log "$*"
}

if [[ -f "$PAUSE_FILE" ]]; then
  log "PAUSED: found $PAUSE_FILE — exit 0"
  exit 0
fi

# --- lock (portable: flock on Linux, mkdir lock elsewhere) ---
LOCK_DIR="${LOCK_FILE}.d"
acquire_lock() {
  if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
      return 1
    fi
    return 0
  fi
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "$$" >"$LOCK_DIR/pid"
    trap 'rm -rf "$LOCK_DIR"' EXIT
    return 0
  fi
  # stale lock?
  if [[ -f "$LOCK_DIR/pid" ]]; then
    local old
    old="$(cat "$LOCK_DIR/pid" 2>/dev/null || true)"
    if [[ -n "$old" ]] && ! kill -0 "$old" 2>/dev/null; then
      rm -rf "$LOCK_DIR"
      if mkdir "$LOCK_DIR" 2>/dev/null; then
        echo "$$" >"$LOCK_DIR/pid"
        trap 'rm -rf "$LOCK_DIR"' EXIT
        return 0
      fi
    fi
  fi
  return 1
}
if ! acquire_lock; then
  log "SKIP: another daily product loop holds $LOCK_FILE"
  exit 0
fi

log "=== daily product loop start weekly=$WEEKLY dry_run=$DRY_RUN skip_deploy=$SKIP_DEPLOY api=$API_URL root=$ROOT_DIR ==="

# =============================================================================
# A. Health — API / onboarding_quest / containers; auto-heal compose if down
# =============================================================================
health_check() {
  local code
  code="$(curl -sS -o /tmp/clawjob-health.json -w '%{http_code}' --max-time 20 "$API_URL/health" 2>/dev/null || echo 000)"
  if [[ "$code" == "200" ]]; then
    HEALTH_OK=1
    note "A health: API OK ($API_URL/health)"
    return 0
  fi
  note "A health: API FAIL http=$code — attempting heal"
  return 1
}

compose_up() {
  if [[ ! -f "$COMPOSE_DIR/$COMPOSE_FILE" ]]; then
    note "A heal: compose file missing — cannot heal"
    return 1
  fi
  if ! command -v docker >/dev/null 2>&1; then
    note "A heal: docker missing"
    return 1
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    note "A heal: dry-run would compose up"
    return 0
  fi
  (
    cd "$COMPOSE_DIR"
    # Never torch-heavy backend rebuild unless explicitly forced
    if [[ "$FORCE_REBUILD_BACKEND" == "1" ]]; then
      docker compose -f "$COMPOSE_FILE" --env-file .env up -d --build --remove-orphans
    else
      docker compose -f "$COMPOSE_FILE" --env-file .env up -d --no-build --remove-orphans
    fi
  ) >>"$LOG_FILE" 2>&1 || true
  sleep 20
  HEALED=1
}

containers_ok() {
  command -v docker >/dev/null 2>&1 || return 1
  local front back
  front="$(docker inspect -f '{{.State.Running}}' clawjob-frontend 2>/dev/null || echo false)"
  back="$(docker inspect -f '{{.State.Running}}' clawjob-backend 2>/dev/null || echo false)"
  [[ "$front" == "true" && "$back" == "true" ]]
}

if ! health_check || ! containers_ok; then
  compose_up || true
  health_check || note "A health: still failing after heal"
  containers_ok && note "A containers: frontend+backend running" || note "A containers: still down / no docker"
else
  note "A containers: frontend+backend running"
fi

# onboarding_quest probe
OQ_JSON="$(curl -fsS --max-time 20 "$API_URL/.well-known/clawjob-agent.json" 2>/dev/null || echo '{}')"
OQ_COUNT="$(python3 -c 'import json,sys; d=json.loads(sys.argv[1] or "{}"); q=d.get("onboarding_quest") or {}; print(int(q.get("count") or 0))' "$OQ_JSON" 2>/dev/null || echo 0)"
if [[ "${OQ_COUNT:-0}" -lt 3 ]]; then
  note "A onboarding_quest: count=$OQ_COUNT (<3) — will reseed in D"
else
  note "A onboarding_quest: count=$OQ_COUNT OK"
fi

# =============================================================================
# B. Metrics snapshot
# =============================================================================
STATS_JSON="$(curl -fsS --max-time 20 "$API_URL/stats" 2>/dev/null || echo '{}')"
python3 - "$METRICS_FILE" "$STATS_JSON" "$OQ_JSON" "$TS_UTC" "$TS_SH" <<'PY' >>"$LOG_FILE" 2>&1 || true
import json, sys
path, stats_s, oq_s, ts_utc, ts_sh = sys.argv[1:6]
try:
    stats = json.loads(stats_s or "{}")
except Exception:
    stats = {}
try:
    oq = json.loads(oq_s or "{}")
except Exception:
    oq = {}
keys = [
    "agents_count_public", "agents_count", "tasks_open", "tasks_completed",
    "rewards_paid", "recent_agents_7d", "skills_published",
]
snap = {k: stats.get(k) for k in keys if k in stats or True}
for k in keys:
    snap.setdefault(k, stats.get(k))
quest = oq.get("onboarding_quest") or {}
out = {
    "ts_utc": ts_utc,
    "ts_shanghai": ts_sh,
    "stats": snap,
    "onboarding_quest": {
        "count": quest.get("count"),
        "ids": quest.get("ids") or oq.get("onboarding_quest_ids"),
    },
    "raw_stats_keys": sorted(list(stats.keys()))[:40],
}
open(path, "w", encoding="utf-8").write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
print(f"metrics written {path}")
print(f"agents_public={snap.get('agents_count_public')} open={snap.get('tasks_open')} completed={snap.get('tasks_completed')} recent_7d={snap.get('recent_agents_7d')}")
PY
note "B metrics: $METRICS_FILE"

# =============================================================================
# C. Competitive pulse — short notes + prioritized TODO
# =============================================================================
competitive_pulse() {
  local mode="$1"  # daily|weekly
  python3 - "$COMP_DOC" "$QUEUE_DOC" "$STATS_JSON" "$APP_URL" "$WEB_URL" "$API_URL" "$mode" "$TS_SH" "$DAY_LOCAL" <<'PY' >>"$LOG_FILE" 2>&1 || true
import json, os, sys, urllib.request
from datetime import datetime

comp_doc, queue_doc, stats_s, app_url, web_url, api_url, mode, ts_sh, day = sys.argv[1:10]
try:
    stats = json.loads(stats_s or "{}")
except Exception:
    stats = {}

checks = []

def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ClawJobDailyLoop/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(8000).decode("utf-8", errors="replace")
            return r.status, body
    except Exception as e:
        return 0, str(e)

# Live site UX pattern checklist (curated vs TaskForce / AgentGigs north-star)
patterns = [
    ("app_home", f"{app_url.rstrip('/')}/", "任务大厅应为一等入口；避免 RL playground 叙事"),
    ("web_home", f"{web_url.rstrip('/')}/", "官网首屏应讲清赚钱闭环：接活→托管→收款"),
    ("join", f"{app_url.rstrip('/')}/#/join", "Join 应突出 Quest→有奖任务主 CTA"),
    ("health", f"{api_url.rstrip('/')}/health", "API 健康"),
    ("stats", f"{api_url.rstrip('/')}/stats", "公开 stats 可读"),
    ("agent_wellknown", f"{api_url.rstrip('/')}/.well-known/clawjob-agent.json", "onboarding_quest 可发现"),
]

for key, url, intent in patterns:
    code, body = fetch(url)
    ok = code == 200
    hint = ""
    low = body.lower()
    if key in ("app_home", "web_home") and ok:
        if "强化学习" in body or "rl playground" in low:
            hint = "文案漂移：出现 RL playground 叙事"
            ok = False
        if "agent" not in low and "任务" not in body:
            hint = "首屏未见任务/Agent 关键词"
    if key == "stats" and ok:
        try:
            d = json.loads(body)
            if int(d.get("tasks_open") or 0) < 1:
                hint = "tasks_open=0 — 供给不足"
        except Exception:
            pass
    checks.append({"id": key, "url": url, "ok": ok, "http": code, "intent": intent, "hint": hint})

todos = []
for c in checks:
    if not c["ok"]:
        pri = "P0" if c["id"] in ("health", "stats", "app_home") else "P1"
        todos.append(f"- [ ] **{pri}** {c['id']}: {c['hint'] or c['intent']} (http={c['http']})")

# Always keep evergreen competitive backlog (safe product directions)
evergreen = [
    ("P1", "信任信号：任务列表第一视口强调奖励 / agent_direct / 信誉入口"),
    ("P1", "Join 路径：唯一主 CTA = 新手 Quest → 有奖任务"),
    ("P2", "Skill 市场与任务大厅并列叙事（差异化 vs TaskForce/AgentGigs）"),
    ("P2", "弱化 KYC/法币提现为首要赚钱路径的文案"),
]
if mode == "weekly":
    evergreen.extend([
        ("P1", "周复盘：对比 TaskForce / AgentGigs 首屏 CTA 数量与结算徽章可见性"),
        ("P2", "周复盘：MCP/文档等次级入口是否挤占首屏"),
        ("P2", "周复盘：社区是否出现运营日报污染（应过滤）"),
    ])

agents = stats.get("agents_count_public")
gap = None
try:
    gap = max(0, 200 - int(agents or 0))
except Exception:
    pass

header = f"""# ClawJob 竞品日常脉搏

> 自动更新：{ts_sh} · mode={mode} · 目标公开 Agent 200（当前 {agents}，缺口 {gap}）

## 当日 live 检查

| id | ok | http | intent |
|----|----|------|--------|
"""
rows = []
for c in checks:
    rows.append(f"| {c['id']} | {'✅' if c['ok'] else '❌'} | {c['http']} | {c['intent']} |")
    if c.get("hint"):
        rows.append(f"| ↳ | | | {c['hint']} |")

body = header + "\n".join(rows) + "\n\n## 当日优先 TODO\n\n"
if todos:
    body += "\n".join(todos) + "\n"
else:
    body += "- [x] live 检查通过（无阻断项）\n"
body += "\n## 常青对标清单\n\n"
for pri, text in evergreen:
    body += f"- [ ] **{pri}** {text}\n"
body += """
## 参考

- `docs/COMPETITIVE_ANALYSIS.md`
- `docs/PLATFORM_NORTH_STAR.md`
- 禁止：假量注册、社区运营日报刷屏、越冷却发帖
"""
os.makedirs(os.path.dirname(comp_doc), exist_ok=True)
open(comp_doc, "w", encoding="utf-8").write(body)

# Merge ranked queue (preserve unchecked human items; refresh auto section)
auto_lines = []
for t in todos:
    auto_lines.append(t)
for pri, text in evergreen[:4]:
    auto_lines.append(f"- [ ] **{pri}** {text}")

queue = f"""# 每日优化队列（DAILY_OPTIMIZATION_QUEUE）

> 大改动（路由/后端/设计系统）只进队列，不由 daily loop 自动改代码。
> 安全自动项仅限：copy/i18n/默认筛选/文档脉搏。末次刷新：{ts_sh}

## Auto（今日）

{chr(10).join(auto_lines) if auto_lines else '- （空）'}

## Manual / larger（人工或全自动 agent）

- [ ] 语义候选人推荐 / Reputation Card 体验打磨（见 NEXT_WAVE）
- [ ] 前端大改前：`FORCE_REBUILD_FRONTEND=1` 验证后再推生产
- [ ] 后端 torch 镜像：仅当 `FORCE_REBUILD_BACKEND=1` 且必要

## 日志

- metrics: `/var/log/clawjob/daily-metrics-{day}.json`
- loop: `/var/log/clawjob/daily-product-loop.log`
"""
open(queue_doc, "w", encoding="utf-8").write(queue)
print(f"competitive written {comp_doc}")
print(f"queue written {queue_doc}")
print(f"failing_checks={sum(1 for c in checks if not c['ok'])}")
PY
  note "C competitive: updated $COMP_DOC + $QUEUE_DOC (mode=$mode)"
}

if [[ "$WEEKLY" == "1" ]]; then
  competitive_pulse weekly
else
  competitive_pulse daily
fi

# =============================================================================
# D. Auto-apply safe product checks
# =============================================================================
run_acquisition_pulse() {
  local acq="$ROOT_DIR/tools/growth/run_daily_acquisition.sh"
  if [[ ! -x "$acq" ]]; then
    chmod +x "$acq" 2>/dev/null || true
  fi
  if [[ ! -f "$acq" ]]; then
    note "D acquisition: missing script — skip"
    return 0
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    note "D acquisition: dry-run would run --pulse"
    return 0
  fi
  # Pulse respects cooldown; does not force-post (avoid spam after 09:05 daily)
  CLAWJOB_ROOT="$ROOT_DIR" CLAWJOB_API_URL="$API_URL" CLAWJOB_OPS_LOG_DIR="$LOG_DIR" \
    "$acq" --pulse >>"$LOG_FILE" 2>&1 || note "D acquisition: pulse warned (non-fatal)"
  note "D acquisition: pulse done"
}

hide_distribute_fakes() {
  if [[ "$DRY_RUN" == "1" ]]; then
    note "D cleanup: dry-run would hide non-real agents"
    return 0
  fi
  if [[ ! -f "$COMPOSE_DIR/$COMPOSE_FILE" ]] || ! command -v docker >/dev/null 2>&1; then
    note "D cleanup: docker/compose unavailable — skip"
    return 0
  fi
  if [[ ! -f "$ROOT_DIR/backend/scripts/cleanup_non_real_agents.py" ]]; then
    note "D cleanup: script missing — skip"
    return 0
  fi
  if (
    cd "$COMPOSE_DIR"
    docker compose -f "$COMPOSE_FILE" exec -T backend \
      sh -c "cd /app && PYTHONPATH=. python3 scripts/cleanup_non_real_agents.py --apply"
  ) >>"$LOG_FILE" 2>&1; then
    note "D cleanup: hide non-real agents OK"
  else
    note "D cleanup: warn (non-fatal)"
  fi
}

run_acquisition_pulse
hide_distribute_fakes
CLAWJOB_API_URL="$API_URL" "$ROOT_DIR/tools/growth/check_milestone.sh" >>"$LOG_FILE" 2>&1 || true

# =============================================================================
# E. Ship cadence — safe copy/docs only; larger items stay in queue
# =============================================================================
# Safe auto-fixes already written COMPETITIVE_DAILY + QUEUE.
# Detect copy drift markers in tracked frontend locales (report only unless trivial).
python3 - "$ROOT_DIR" "$QUEUE_DOC" "$DRY_RUN" <<'PY' >>"$LOG_FILE" 2>&1 || true
import os, re, sys
root, queue_doc, dry = sys.argv[1], sys.argv[2], sys.argv[3]
bad_patterns = [
    (re.compile(r"RL\s*playground", re.I), "RL playground 叙事"),
    (re.compile(r"强化学习试验"), "强化学习试验场 叙事"),
]
hits = []
for rel in ("frontend/src/i18n/zh-CN.ts", "frontend/src/i18n/en.ts", "frontend/index.html"):
    path = os.path.join(root, rel)
    if not os.path.isfile(path):
        continue
    text = open(path, encoding="utf-8").read()
    for rx, label in bad_patterns:
        if rx.search(text):
            hits.append(f"{rel}: {label}")
if hits:
    with open(queue_doc, "a", encoding="utf-8") as f:
        f.write("\n## Drift detected（需人工/安全 PR）\n\n")
        for h in hits:
            f.write(f"- [ ] **P0** copy drift — {h}\n")
    print("E drift: " + "; ".join(hits))
else:
    print("E drift: none in locale/index.html")
PY
note "E ship: queue refreshed; no unsafe code auto-apply"

# =============================================================================
# F. Deploy — pull main if newer than last deploy SHA; frontend rebuild only
# =============================================================================
ensure_mirror() {
  mkdir -p "$(dirname "$MIRROR_DIR")"
  if [[ ! -d "$MIRROR_DIR/.git" ]]; then
    log "F mirror: cloning $GIT_REMOTE → $MIRROR_DIR"
    if [[ "$DRY_RUN" == "1" ]]; then
      note "F deploy: dry-run would clone mirror"
      return 1
    fi
    rm -rf "$MIRROR_DIR"
    git clone --depth 30 --branch "$GIT_BRANCH" "$GIT_REMOTE" "$MIRROR_DIR" >>"$LOG_FILE" 2>&1
  fi
  (
    cd "$MIRROR_DIR"
    git fetch --depth 30 origin "$GIT_BRANCH" >>"$LOG_FILE" 2>&1
    git checkout -q "$GIT_BRANCH" 2>/dev/null || git checkout -q -B "$GIT_BRANCH" "origin/$GIT_BRANCH"
    git reset --hard "origin/$GIT_BRANCH" >>"$LOG_FILE" 2>&1
  )
}

sync_from_mirror() {
  # Preserve runtime secrets & growth state
  rsync -a \
    --exclude 'deploy/.env' \
    --exclude 'tools/growth/.distribution_state.json' \
    --exclude 'tools/growth/.acquisition_paused' \
    --exclude 'tools/growth/.daily_loop_paused' \
    --exclude 'tools/growth/.last_daily_deploy_sha' \
    --exclude 'tools/growth/*.log' \
    --exclude '.src-mirror/' \
    --exclude '.openclaw-cli/' \
    --exclude 'bin/openclaw' \
    --exclude 'bin/node' \
    --exclude 'logs/' \
    --exclude 'node_modules/' \
    --exclude 'frontend/dist/' \
    --exclude '.git/' \
    --exclude '**/__pycache__/' \
    "$MIRROR_DIR/" "$ROOT_DIR/"
}

deploy_frontend() {
  (
    cd "$COMPOSE_DIR"
    export FORCE_REBUILD_FRONTEND=1
    echo "F deploy: building frontend (no-cache)..."
    docker compose -f "$COMPOSE_FILE" --env-file .env build --no-cache frontend
    docker compose -f "$COMPOSE_FILE" --env-file .env up -d --no-deps --no-build frontend
    if [[ "$FORCE_REBUILD_BACKEND" == "1" ]]; then
      echo "F deploy: FORCE_REBUILD_BACKEND=1 — rebuilding backend"
      docker compose -f "$COMPOSE_FILE" --env-file .env up -d --build backend
    else
      # Ensure backend stays up without rebuild
      docker compose -f "$COMPOSE_FILE" --env-file .env up -d --no-deps --no-build backend || true
    fi
  ) >>"$LOG_FILE" 2>&1
}

if [[ "$SKIP_DEPLOY" == "1" ]]; then
  note "F deploy: skipped (--skip-deploy)"
elif [[ "$DRY_RUN" == "1" ]]; then
  note "F deploy: dry-run skip"
else
  if ensure_mirror; then
    NEW_SHA="$(cd "$MIRROR_DIR" && git rev-parse HEAD)"
    OLD_SHA=""
    [[ -f "$LAST_DEPLOY_SHA_FILE" ]] && OLD_SHA="$(tr -d '[:space:]' <"$LAST_DEPLOY_SHA_FILE" || true)"
    if [[ -z "$OLD_SHA" && "${FORCE_FIRST_DEPLOY:-0}" != "1" ]]; then
      # Bootstrap: record tip without rebuild (avoids surprise no-cache frontend on day-0)
      sync_from_mirror
      chmod +x "$ROOT_DIR/tools/growth/"*.sh 2>/dev/null || true
      echo "$NEW_SHA" >"$LAST_DEPLOY_SHA_FILE"
      DEPLOY_SHA="$NEW_SHA"
      note "F deploy: bootstrap last sha=$NEW_SHA (no rebuild; set FORCE_FIRST_DEPLOY=1 to force)"
    elif [[ -n "$OLD_SHA" && "$NEW_SHA" == "$OLD_SHA" ]]; then
      note "F deploy: already at $NEW_SHA — no ship"
    else
      # Guard: only deploy clean main tip (mirror is reset --hard origin/main)
      note "F deploy: new commits ${OLD_SHA:-none} → $NEW_SHA — sync + frontend rebuild"
      sync_from_mirror
      chmod +x "$ROOT_DIR/tools/growth/"*.sh 2>/dev/null || true
      if deploy_frontend; then
        # post-deploy health gate
        sleep 15
        if curl -fsS --max-time 20 "$API_URL/health" >/dev/null 2>&1; then
          echo "$NEW_SHA" >"$LAST_DEPLOY_SHA_FILE"
          DEPLOYED=1
          DEPLOY_SHA="$NEW_SHA"
          note "F deploy: OK sha=$NEW_SHA recorded"
        else
          note "F deploy: health failed after deploy — NOT updating last sha"
        fi
      else
        note "F deploy: frontend build/up failed — see log"
      fi
    fi
  else
    note "F deploy: mirror unavailable"
  fi
fi

# =============================================================================
# G. Notify — ops memory / log; soft-skip Feishu
# =============================================================================
{
  echo "# Daily product loop summary — $TS_SH"
  echo
  echo "- weekly=$WEEKLY dry_run=$DRY_RUN healed=$HEALED deployed=$DEPLOYED sha=${DEPLOY_SHA:-n/a}"
  echo "- metrics: $METRICS_FILE"
  echo "- competitive: $COMP_DOC"
  echo "- queue: $QUEUE_DOC"
  echo
  echo "## Notes"
  for line in "${SUMMARY_LINES[@]}"; do
    echo "- $line"
  done
} >"$SUMMARY_FILE"
cp "$SUMMARY_FILE" "$LOG_DIR/daily-product-latest.md" 2>/dev/null || true
note "G summary: $SUMMARY_FILE"

# Soft-skip Feishu / OpenClaw notify
if [[ "$DRY_RUN" != "1" ]]; then
  # shellcheck source=resolve_openclaw.sh
  if [[ -f "$ROOT_DIR/tools/growth/resolve_openclaw.sh" ]]; then
    # shellcheck disable=SC1091
    source "$ROOT_DIR/tools/growth/resolve_openclaw.sh"
    if resolve_openclaw_bin && openclaw_feishu_configured; then
      log "G notify: Feishu configured — optional mission soft path"
      if [[ -x "$ROOT_DIR/tools/community_ops/openclaw_mission.sh" ]]; then
        CLAWJOB_ROOT="$ROOT_DIR" CLAWJOB_API_URL="$API_URL" CLAWJOB_OPS_LOG_DIR="$LOG_DIR" \
          OPENCLAW_BIN="$OPENCLAW_BIN" \
          "$ROOT_DIR/tools/community_ops/openclaw_mission.sh" >>"$LOG_FILE" 2>&1 \
          || log "G notify: openclaw_mission soft-failed"
      fi
    else
      log "G notify: soft-skip Feishu (no creds / no CLI)"
    fi
  else
    log "G notify: soft-skip (resolve_openclaw.sh missing)"
  fi
fi

log "=== daily product loop done deployed=$DEPLOYED ==="
exit 0
