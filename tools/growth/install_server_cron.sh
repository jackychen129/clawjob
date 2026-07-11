#!/usr/bin/env bash
# 在 Linux 生产机安装 ClawJob 拉新 crontab（非 macOS launchd）
# 用法（服务器上）：
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_server_cron.sh
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_server_cron.sh --uninstall
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
MARKER="# clawjob-acquisition"
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-/var/log/clawjob}"
API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
RUNNER="$ROOT_DIR/tools/growth/run_daily_acquisition.sh"

UNINSTALL=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    -h|--help)
      sed -n '2,7p' "$0"
      exit 0
      ;;
  esac
done

if [[ ! -x "$RUNNER" ]]; then
  chmod +x "$RUNNER" "$ROOT_DIR/tools/growth/"*.sh 2>/dev/null || true
fi
if [[ ! -f "$RUNNER" ]]; then
  echo "ERROR: missing $RUNNER" >&2
  exit 1
fi

mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

# Remove previous clawjob-acquisition blocks
TMP="$(mktemp)"
crontab -l 2>/dev/null | awk -v m="$MARKER" '
  $0 ~ m" begin" {skip=1; next}
  $0 ~ m" end" {skip=0; next}
  skip {next}
  {print}
' >"$TMP" || true

if [[ "$UNINSTALL" == "1" ]]; then
  crontab "$TMP"
  rm -f "$TMP"
  echo "Uninstalled clawjob-acquisition crontab entries."
  exit 0
fi

{
  cat "$TMP"
  cat <<EOF

${MARKER} begin
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CLAWJOB_ROOT=${ROOT_DIR}
CLAWJOB_API_URL=${API_URL}
CLAWJOB_OPS_LOG_DIR=${LOG_DIR}
# Daily 09:05 Asia/Shanghai — full acquisition
5 9 * * * cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} ${RUNNER} >> ${LOG_DIR}/acquisition-cron.log 2>&1
# Every 6h — distribution pulse
0 */6 * * * cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} ${RUNNER} --pulse >> ${LOG_DIR}/acquisition-cron.log 2>&1
${MARKER} end
EOF
} | crontab -

rm -f "$TMP"
echo "Installed clawjob-acquisition cron:"
echo "  daily  09:05  ${RUNNER}"
echo "  pulse  */6h   ${RUNNER} --pulse"
echo "  logs   ${LOG_DIR}/"
echo "Pause:  touch ${ROOT_DIR}/tools/growth/.acquisition_paused"
echo "Verify: crontab -l | grep clawjob-acquisition"
crontab -l | grep -A20 "clawjob-acquisition begin" || true
