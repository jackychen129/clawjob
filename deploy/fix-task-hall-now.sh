#!/bin/bash
# 本机执行：一键修复线上任务大厅（不同步代码，只修补 .env 并启动/重建 frontend+backend）
# 用法：cd /path/to/clawjob && bash deploy/fix-task-hall-now.sh
# 输出会同时打印并写入 deploy/fix-task-hall-now.log

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/fix-task-hall-now.log"
exec > >(tee -a "$LOG") 2>&1

echo "========== $(date '+%Y-%m-%d %H:%M:%S') 修复任务大厅 =========="
cd "$SCRIPT_DIR/.."

[ -f deploy/.deploy_env ] && set -a && . deploy/.deploy_env && set +a
[ -f deploy/ssh_key_fallback.sh ] && . deploy/ssh_key_fallback.sh
SERVER_IP="${SERVER_IP:-43.99.97.240}"

echo "目标: ${SERVER_IP}"
echo ""

# 1. 先尝试只启动容器（不 build），避免 SSH 长时间断开
echo ">>> 修补 .env 并启动 frontend + backend（不重新 build）..."
SKIP_BUILD=1 bash deploy/ensure-task-hall-on-server.sh 2>&1 | sed 's/^/  /' || true
echo ""

# 2. 本机验证
echo ">>> 本机访问任务大厅（5 秒超时）"
CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${SERVER_IP}:3000/" 2>/dev/null || echo "000")
echo "  http://${SERVER_IP}:3000 → HTTP $CODE"
if [ "$CODE" = "200" ]; then
  echo ""
  echo "========== 修复成功：任务大厅可访问 =========="
  echo "请用浏览器打开: http://${SERVER_IP}:3000"
else
  echo ""
  echo "========== 若仍打不开，请检查 =========="
  echo "1. 阿里云轻量控制台 → 该实例 → 防火墙 → 入站规则是否有 TCP 3000，来源 0.0.0.0/0"
  echo "2. 把本文件内容发给我继续排查: cat deploy/fix-task-hall-now.log"
fi
echo ""
echo "日志已保存: $LOG"
