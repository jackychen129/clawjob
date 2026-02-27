#!/bin/bash
# 一键修复线上环境：修补 .env、重建前后端、跑 API 验证。
# 在本机执行（需能 SSH 到服务器）：cd /path/to/clawjob && bash deploy/repair-online.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."
[ -f deploy/.deploy_env ] && set -a && . deploy/.deploy_env && set +a
SERVER_IP="${SERVER_IP:-43.99.97.240}"

echo "========== 1. 修补 .env 并重建任务大厅 =========="
bash deploy/ensure-task-hall-on-server.sh || true
echo ""

echo "========== 2. 完整检查与 API 验证 =========="
bash deploy/check-and-fix-online.sh || true
echo ""

echo "========== 修复流程结束 =========="
echo "任务大厅: http://${SERVER_IP}:3000"
echo "后端 API: http://${SERVER_IP}:8000"
