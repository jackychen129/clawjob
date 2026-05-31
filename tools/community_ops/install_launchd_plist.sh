#!/usr/bin/env bash
# 安装 macOS launchd 定时任务（社区运营 + Agent 审计）
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
LABEL_PREFIX="com.clawjob.ops"

install_plist() {
  local name="$1"
  local interval_sec="$2"
  local script="$3"
  local plist="$PLIST_DIR/${LABEL_PREFIX}.${name}.plist"

  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL_PREFIX}.${name}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${script}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${ROOT_DIR}</string>
  <key>StartInterval</key>
  <integer>${interval_sec}</integer>
  <key>StandardOutPath</key>
  <string>${ROOT_DIR}/logs/launchd-${name}.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT_DIR}/logs/launchd-${name}.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAWJOB_API_URL</key>
    <string>${CLAWJOB_API_URL:-https://api.clawjob.com.cn}</string>
  </dict>
</dict>
</plist>
EOF

  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "Installed: $plist (every ${interval_sec}s)"
}

mkdir -p "$ROOT_DIR/logs" "$PLIST_DIR"
chmod +x "$ROOT_DIR/tools/community_ops/run_community_ops.sh"
chmod +x "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh" 2>/dev/null || true

# 每 15 分钟：社区热度 / dispatch
install_plist "community-ops" 900 "$ROOT_DIR/tools/community_ops/run_community_ops.sh"

# 每 6 小时：Agent 增长日志（独立跑一次 monitor）
cat > "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT_DIR/logs"
python3 "$ROOT_DIR/tools/monitor_agent_growth.py" --check-only >> "$ROOT_DIR/logs/agent_growth.log" 2>&1
EOS
chmod +x "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh"
install_plist "agent-growth" 21600 "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh"

# 每天：audit_agents dry-run
cat > "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT_DIR/logs"
cd "$ROOT_DIR/backend"
python3 scripts/audit_agents.py >> "$ROOT_DIR/logs/audit_agents.log" 2>&1
EOS
chmod +x "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh"
install_plist "audit-agents" 86400 "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh"

echo ""
echo "Done. Logs: $ROOT_DIR/logs/"
echo "Uninstall: launchctl unload ~/Library/LaunchAgents/${LABEL_PREFIX}.*.plist"
