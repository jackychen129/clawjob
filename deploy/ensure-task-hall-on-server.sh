#!/bin/bash
# 本机执行：SSH 到服务器，修补 .env 的 API/CORS 为当前 SERVER_IP，并重建/启动 frontend 与 backend。
# 用于「任务大厅打不开」时快速修复，无需完整重新部署。
# 用法：cd /path/to/clawjob && bash deploy/ensure-task-hall-on-server.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
[ -f "$SCRIPT_DIR/ssh_key_fallback.sh" ] && . "$SCRIPT_DIR/ssh_key_fallback.sh"
SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
if [ -z "$DEPLOY_SSH_KEY" ] || [ ! -f "$KEY" ]; then
  echo "错误：未找到 SSH 私钥。请任选其一："
  echo "  1) 在 deploy/.deploy_env 中设置：DEPLOY_SSH_KEY=/path/to/你的密钥.pem"
  echo "  2) 或将私钥放到 ~/.ssh/id_rsa / ~/.ssh/id_ed25519"
  exit 1
fi

# 保活避免长时间 Docker 构建时 SSH 断开（grpc: the client connection is closing）
SSH_KEEPALIVE="-o ServerAliveInterval=60 -o ServerAliveCountMax=10"
SSH_CMD="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $SSH_KEEPALIVE"
TARGET="${SSH_USER}@${SERVER_IP}"

# SKIP_BUILD=1 时只启动容器不构建，速度快、不易断线
if [ -n "$SKIP_BUILD" ]; then
  echo ">>> 目标: ${TARGET}，修补 .env 并启动任务大厅（不构建）..."
  UP_CMD="up -d"
else
  echo ">>> 目标: ${TARGET}，修补 .env 并重建任务大厅..."
  UP_CMD="up -d --build"
fi

$SSH_CMD "$TARGET" "set -e
  cd ${REMOTE_DIR}/deploy
  [ ! -f .env ] && cp .env.example .env
  SIP='${SERVER_IP}'
  grep -q '^VITE_API_BASE_URL=' .env && sed -i.bak \"s|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://\$SIP:8000|\" .env || echo \"VITE_API_BASE_URL=http://\$SIP:8000\" >> .env
  grep -q '^CORS_ORIGINS=' .env && sed -i.bak \"s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://\$SIP:3000|\" .env || echo \"CORS_ORIGINS=http://\$SIP:3000\" >> .env
  grep -q '^FRONTEND_URL=' .env && sed -i.bak \"s|^FRONTEND_URL=.*|FRONTEND_URL=http://\$SIP:3000|\" .env || echo \"FRONTEND_URL=http://\$SIP:3000\" >> .env
  echo '启动 frontend + backend...'
  docker compose -f docker-compose.prod.yml --env-file .env $UP_CMD frontend backend
  echo '等待 25 秒...'
  sleep 25
  docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
  echo ''
  echo '任务大厅: http://${SERVER_IP}:3000'
  echo '若仍打不开，请到阿里云控制台放行 TCP 3000。'
"
echo "完成。"
