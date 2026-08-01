#!/usr/bin/env bash
# 在 Linux 生产机安装 ClawJob 拉新 + 每日产品优化 crontab（非 macOS launchd）
# 用法（服务器上）：
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_server_cron.sh
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_server_cron.sh --uninstall
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_server_cron.sh --uninstall-daily-product
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
MARKER="# clawjob-acquisition"
MARKER_DAILY="# clawjob-daily-product"
LOG_DIR="${CLAWJOB_OPS_LOG_DIR:-/var/log/clawjob}"
API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
RUNNER="$ROOT_DIR/tools/growth/run_daily_acquisition.sh"
DAILY_RUNNER="$ROOT_DIR/tools/growth/run_daily_product_loop.sh"

UNINSTALL=0
UNINSTALL_DAILY_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    --uninstall-daily-product) UNINSTALL_DAILY_ONLY=1 ;;
    -h|--help)
      sed -n '2,8p' "$0"
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
if [[ ! -f "$DAILY_RUNNER" ]]; then
  echo "ERROR: missing $DAILY_RUNNER" >&2
  exit 1
fi
chmod +x "$DAILY_RUNNER" 2>/dev/null || true

mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

strip_marker_block() {
  local marker="$1"
  local infile="$2"
  local outfile="$3"
  awk -v m="$marker" '
    $0 ~ m" begin" {skip=1; next}
    $0 ~ m" end" {skip=0; next}
    skip {next}
    {print}
  ' "$infile" >"$outfile" || true
}

TMP="$(mktemp)"
TMP2="$(mktemp)"
crontab -l 2>/dev/null >"$TMP" || true
strip_marker_block "$MARKER_DAILY" "$TMP" "$TMP2"
mv "$TMP2" "$TMP"

if [[ "$UNINSTALL_DAILY_ONLY" == "1" ]]; then
  crontab "$TMP"
  rm -f "$TMP"
  echo "Uninstalled clawjob-daily-product crontab entries (acquisition kept)."
  exit 0
fi

strip_marker_block "$MARKER" "$TMP" "$TMP2"
mv "$TMP2" "$TMP"

if [[ "$UNINSTALL" == "1" ]]; then
  crontab "$TMP"
  rm -f "$TMP"
  echo "Uninstalled clawjob-acquisition + clawjob-daily-product crontab entries."
  exit 0
fi

{
  cat "$TMP"
  cat <<EOF

${MARKER} begin
SHELL=/bin/bash
PATH=${ROOT_DIR}/bin:${ROOT_DIR}/.openclaw-cli/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CLAWJOB_ROOT=${ROOT_DIR}
CLAWJOB_API_URL=${API_URL}
CLAWJOB_OPS_LOG_DIR=${LOG_DIR}
OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli
# Daily 09:05 Asia/Shanghai — full acquisition
5 9 * * * cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli ${RUNNER} >> ${LOG_DIR}/acquisition-cron.log 2>&1
# Every 6h — distribution pulse
0 */6 * * * cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli ${RUNNER} --pulse >> ${LOG_DIR}/acquisition-cron.log 2>&1
${MARKER} end

${MARKER_DAILY} begin
SHELL=/bin/bash
PATH=${ROOT_DIR}/bin:${ROOT_DIR}/.openclaw-cli/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
CLAWJOB_ROOT=${ROOT_DIR}
CLAWJOB_API_URL=${API_URL}
CLAWJOB_OPS_LOG_DIR=${LOG_DIR}
OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli
# Daily 10:00 Asia/Shanghai — product+ops optimization loop (after 09:05 acquisition)
0 10 * * * cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli ${DAILY_RUNNER} >> ${LOG_DIR}/daily-product-cron.log 2>&1
# Sunday 10:30 — deeper competitive review
30 10 * * 0 cd ${ROOT_DIR} && CLAWJOB_ROOT=${ROOT_DIR} CLAWJOB_API_URL=${API_URL} CLAWJOB_OPS_LOG_DIR=${LOG_DIR} OPENCLAW_PREFIX=${ROOT_DIR}/.openclaw-cli ${DAILY_RUNNER} --weekly >> ${LOG_DIR}/daily-product-cron.log 2>&1
${MARKER_DAILY} end
EOF
} | crontab -

rm -f "$TMP"
echo "Installed clawjob-acquisition + clawjob-daily-product cron:"
echo "  acquisition daily  09:05  ${RUNNER}"
echo "  acquisition pulse  */6h   ${RUNNER} --pulse"
echo "  product    daily   10:00  ${DAILY_RUNNER}"
echo "  product    weekly  Sun 10:30  ${DAILY_RUNNER} --weekly"
echo "  logs   ${LOG_DIR}/"
echo "Pause acquisition: touch ${ROOT_DIR}/tools/growth/.acquisition_paused"
echo "Pause product loop: touch ${ROOT_DIR}/tools/growth/.daily_loop_paused"
echo "Verify: crontab -l | grep -E 'clawjob-(acquisition|daily-product)'"
crontab -l | grep -A30 "clawjob-acquisition begin" || true
crontab -l | grep -A20 "clawjob-daily-product begin" || true
