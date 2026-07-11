#!/usr/bin/env bash
# 安装 macOS launchd 定时任务（社区运营 + Agent 审计）
set -euo pipefail

# Prefer explicit CLAWJOB_ROOT (e.g. ~/Projects/clawjob) so plist does not point at Documents.
SCRIPT_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ROOT_DIR="${CLAWJOB_ROOT:-$SCRIPT_ROOT}"
if [ ! -d "$ROOT_DIR/tools/community_ops" ]; then
  echo "ERROR: CLAWJOB_ROOT=$ROOT_DIR 不是有效的 clawjob 仓库（缺少 tools/community_ops）" >&2
  exit 1
fi
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
PLIST_DIR="$HOME/Library/LaunchAgents"
LABEL_PREFIX="com.clawjob.ops"
# launchd 后台进程无法访问 ~/Documents 等受 TCC 保护目录；WorkingDirectory 用 $HOME
LAUNCHD_CWD="${HOME}"
# Logs outside Documents/Desktop/Downloads so launchd can write even if repo is TCC-blocked.
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-$HOME/Library/Logs/clawjob}"

warn_protected_path() {
  case "$ROOT_DIR" in
    "$HOME/Documents"/*|"${HOME}/Desktop"/*|"${HOME}/Downloads"/*)
      echo ""
      echo "⚠️  仓库位于 macOS 受保护目录：$ROOT_DIR"
      echo "   launchd 后台会被 TCC 拦截（exit 126 / Operation not permitted）。"
      echo "   推荐复制粘贴："
      echo "     mkdir -p ~/Projects && cp -R \"$ROOT_DIR\" ~/Projects/clawjob"
      echo "     # 或直接 mv（确认无其他进程占用后）"
      echo "     # mv \"$ROOT_DIR\" ~/Projects/clawjob"
      echo "     cd ~/Projects/clawjob && CLAWJOB_ROOT=\"\$(pwd)\" ./tools/community_ops/install_launchd_plist.sh"
      echo "   或：系统设置 → 隐私与安全性 → 完全磁盘访问权限 → 添加 /bin/bash + Terminal"
      echo "   日志已写到 $LOG_DIR（不受 Documents TCC 影响）；但脚本本身仍须能读仓库。"
      echo "   详见 tools/community_ops/README.md"
      echo ""
      ;;
  esac
}

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
  <string>${LAUNCHD_CWD}</string>
  <key>StartInterval</key>
  <integer>${interval_sec}</integer>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd-${name}.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd-${name}.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAWJOB_ROOT</key>
    <string>${ROOT_DIR}</string>
    <key>CLAWJOB_OPS_LOG_DIR</key>
    <string>${LOG_DIR}</string>
    <key>CLAWJOB_API_URL</key>
    <string>${CLAWJOB_API_URL:-https://api.clawjob.com.cn}</string>
    <key>HOME</key>
    <string>${HOME}</string>
  </dict>
</dict>
</plist>
EOF

  launchctl unload "$plist" 2>/dev/null || true
  launchctl load "$plist"
  echo "Installed: $plist (every ${interval_sec}s, CLAWJOB_ROOT=$ROOT_DIR, logs=$LOG_DIR)"
}

warn_protected_path
mkdir -p "$LOG_DIR" "$ROOT_DIR/logs" "$PLIST_DIR"
# Keep a convenience symlink when repo logs/ is writable; ignore failures under TCC.
ln -sfn "$LOG_DIR" "$ROOT_DIR/logs/launchd-external" 2>/dev/null || true
chmod +x "$ROOT_DIR"/tools/community_ops/*.sh 2>/dev/null || true
chmod +x "$ROOT_DIR"/tools/growth/*.sh 2>/dev/null || true
chmod +x "$ROOT_DIR/tools/community_ops/run_community_ops.sh"
chmod +x "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh" 2>/dev/null || true

# 每 15 分钟：社区热度 / dispatch
install_plist "community-ops" 900 "$ROOT_DIR/tools/community_ops/run_community_ops.sh"

# 每 6 小时：Agent 增长日志（独立跑一次 monitor）
cat > "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh" <<EOS
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="\${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "\$ROOT_DIR" || exit 1
mkdir -p "\$ROOT_DIR/logs"
python3 "\$ROOT_DIR/tools/monitor_agent_growth.py" --check-only >> "\$ROOT_DIR/logs/agent_growth.log" 2>&1
EOS
chmod +x "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh"
install_plist "agent-growth" 21600 "$ROOT_DIR/tools/community_ops/agent_growth_6h.sh"

# 每天：audit_agents dry-run
cat > "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh" <<EOS
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="\${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "\$ROOT_DIR/backend" || exit 1
mkdir -p "\$ROOT_DIR/logs"
python3 scripts/audit_agents.py >> "\$ROOT_DIR/logs/audit_agents.log" 2>&1
EOS
chmod +x "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh"
install_plist "audit-agents" 86400 "$ROOT_DIR/tools/community_ops/audit_agents_daily.sh"

# 每日 09:00：OpenClaw 社区 recap（openclaw_mission）
chmod +x "$ROOT_DIR/tools/community_ops/openclaw_mission.sh"
OPENCLAW_PLIST="$PLIST_DIR/${LABEL_PREFIX}.openclaw-mission.plist"
cat > "$OPENCLAW_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL_PREFIX}.openclaw-mission</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${ROOT_DIR}/tools/community_ops/openclaw_mission.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${LAUNCHD_CWD}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>9</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_DIR}/launchd-openclaw-mission.log</string>
  <key>StandardErrorPath</key>
  <string>${LOG_DIR}/launchd-openclaw-mission.err.log</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>CLAWJOB_ROOT</key>
    <string>${ROOT_DIR}</string>
    <key>CLAWJOB_OPS_LOG_DIR</key>
    <string>${LOG_DIR}</string>
    <key>CLAWJOB_API_URL</key>
    <string>${CLAWJOB_API_URL:-https://api.clawjob.com.cn}</string>
    <key>HOME</key>
    <string>${HOME}</string>
  </dict>
</dict>
</plist>
EOF
launchctl unload "$OPENCLAW_PLIST" 2>/dev/null || true
launchctl load "$OPENCLAW_PLIST"
echo "Installed: $OPENCLAW_PLIST (daily 09:00, CLAWJOB_ROOT=$ROOT_DIR)"

echo ""
echo "Done. Logs: $LOG_DIR"
echo "Verify: CLAWJOB_ROOT=$ROOT_DIR $ROOT_DIR/tools/community_ops/run_community_ops.sh"
echo "Uninstall: launchctl unload ~/Library/LaunchAgents/${LABEL_PREFIX}.*.plist"
