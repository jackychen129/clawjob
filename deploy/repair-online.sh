#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"
[ -f deploy/.deploy_env ] && set -a && . deploy/.deploy_env && set +a
[ -f deploy/ssh_key_fallback.sh ] && . deploy/ssh_key_fallback.sh

SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

# NOTE: translated comment in English.
if [ -n "$DEPLOY_SSH_KEY" ]; then
  KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  [ -f "$KEY" ] && RSYNC_RSH="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
fi
RSYNC_RSH="${RSYNC_RSH:-ssh -o StrictHostKeyChecking=accept-new}"

echo "========== 0. 同步代码到服务器 =========="
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '**/__pycache__' \
  --exclude 'frontend/dist' \
  --exclude 'backend/.pytest_cache' \
  --exclude '*.pyc' \
  ${RSYNC_RSH:+-e "$RSYNC_RSH"} \
  "$REPO_ROOT/" "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}/"
echo ""

echo "========== 1. 修补 .env 并重建任务大厅 =========="
bash deploy/ensure-task-hall-on-server.sh || true
echo ""

echo "========== 2. 完整检查与 API 验证 =========="
bash deploy/check-and-fix-online.sh || true
echo ""

echo "========== 3. 线上 API 功能验证 =========="
export CLAWJOB_API_URL="http://${SERVER_IP}:8000"
python3 deploy/verify-deployed.py || true
echo ""

echo "========== 修复并更新流程结束 =========="
echo "任务大厅: http://${SERVER_IP}:3000"
echo "后端 API: http://${SERVER_IP}:8000"
