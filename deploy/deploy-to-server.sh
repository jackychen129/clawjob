#!/bin/bash
# 本机执行：将 ClawJob 代码同步到轻量服务器并启动 Docker 栈
# 用法： SERVER_IP=你的公网IP [SSH_USER=root] [REMOTE_DIR=/opt/clawjob] ./deploy/deploy-to-server.sh
#
# 首次部署前请在本机或服务器上准备好 deploy/.env（从 .env.example 复制并修改域名、密码、JWT_SECRET、Google OAuth 等）

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$(dirname "$0")"
cd "$REPO_ROOT"

# 从 deploy/.deploy_env 读取 SERVER_IP 及可选 DEPLOY_SSH_PASSWORD / DEPLOY_SSH_KEY
if [ -f "${DEPLOY_DIR}/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${DEPLOY_DIR}/.deploy_env"
  set +a
fi
export DEPLOY_SSH_KEY
export DEPLOY_SSH_PASSWORD

SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

if [ -z "$SERVER_IP" ]; then
  echo "请设置服务器公网 IP，例如："
  echo "  SERVER_IP=47.74.xxx.xxx ./deploy/deploy-to-server.sh"
  echo ""
  echo "可选：SSH_USER=root REMOTE_DIR=/opt/clawjob"
  echo "解决 Permission denied (publickey)：见下方 SSH_KEY / SSH_PASSWORD 说明"
  exit 1
fi

# 默认使用 newclawjobkey.pem（未设置 DEPLOY_SSH_KEY 且该文件存在时）
if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

# 解决 Permission denied (publickey)：支持指定密钥或密码，否则用本机默认 SSH
SSH_OPTS=""
RSYNC_RSH=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass。请先安装：brew install sshpass 或 sudo apt install sshpass"
    exit 1
  fi
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  RSYNC_RSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  if [ ! -f "$DEPLOY_SSH_KEY" ]; then
    echo "错误：DEPLOY_SSH_KEY 指向的文件不存在: $DEPLOY_SSH_KEY"
    exit 1
  fi
  SSH_OPTS="-i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
elif [ -f "${DEPLOY_DIR}/.ssh/id_ed25519" ]; then
  SSH_OPTS="-i ${DEPLOY_DIR}/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
elif [ -f "${DEPLOY_DIR}/.ssh/id_rsa" ]; then
  SSH_OPTS="-i ${DEPLOY_DIR}/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
else
  SSH_OPTS="-o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
fi

# 部署前 SSH 预检
if ! $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" &>/dev/null; then
  echo "错误：无法 SSH 登录 ${SSH_USER}@${SERVER_IP}。请配置 DEPLOY_SSH_PASSWORD 或密钥，见 deploy/README_DEPLOY_ALL.md"
  exit 1
fi

# 避免 SSH Host key verification failed
if ! ssh-keygen -F "$SERVER_IP" &>/dev/null 2>&1; then
  echo ">>> 将 ${SERVER_IP} 加入 known_hosts..."
  ssh-keyscan -H "$SERVER_IP" 2>/dev/null >> ~/.ssh/known_hosts 2>/dev/null || true
fi

echo ">>> 目标: ${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}"
echo ">>> 同步代码（排除 node_modules、.git、__pycache__、frontend/dist）..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '**/__pycache__' \
  --exclude 'frontend/dist' \
  --exclude 'backend/.pytest_cache' \
  --exclude '*.pyc' \
  ${RSYNC_RSH:+-e "$RSYNC_RSH"} \
  "$REPO_ROOT/" "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}/"

echo ">>> 在服务器上检查 .env 并启动 Docker..."
# 将 SERVER_IP 注入到远程脚本（用于修补 .env）
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "set -e
  cd ${REMOTE_DIR}/deploy
  if [ ! -f .env ]; then
    cp .env.example .env
    echo ''
    echo '已在服务器上创建 deploy/.env，请先编辑并填入真实配置后重新运行本脚本：'
    echo \"  ssh ${SSH_USER}@${SERVER_IP} 'vim ${REMOTE_DIR}/deploy/.env'\"
    echo '  必改：VITE_API_BASE_URL、FRONTEND_URL、CORS_ORIGINS、POSTGRES_PASSWORD、DATABASE_URL、REDIS_PASSWORD、REDIS_URL、JWT_SECRET'
    echo ''
    exit 1
  fi
  SIP='${SERVER_IP}'
  grep -q '^VITE_API_BASE_URL=' .env && sed -i.bak \"s|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://\$SIP:8000|\" .env || echo \"VITE_API_BASE_URL=http://\$SIP:8000\" >> .env
  grep -q '^CORS_ORIGINS=' .env && sed -i.bak \"s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://\$SIP:3000|\" .env || echo \"CORS_ORIGINS=http://\$SIP:3000\" >> .env
  grep -q '^FRONTEND_URL=' .env && sed -i.bak \"s|^FRONTEND_URL=.*|FRONTEND_URL=http://\$SIP:3000|\" .env || echo \"FRONTEND_URL=http://\$SIP:3000\" >> .env
  echo '启动 Docker Compose（已按 SERVER_IP 修补 VITE_API_BASE_URL / CORS_ORIGINS）...'
  docker compose -f docker-compose.prod.yml --env-file .env up -d --build
  echo ''
  echo '等待服务就绪（约 30 秒）...'
  sleep 30
  docker compose -f docker-compose.prod.yml ps
  echo ''
  echo '>>> 首次部署建议执行数据库初始化：'
  echo \"  ssh ${SSH_USER}@${SERVER_IP} 'cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c \"PYTHONPATH=. python3 -c \\\"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\\\"\"'
  echo ''
  echo '>>> 访问：'
  echo \"  前端（任务大厅）: http://${SERVER_IP}:3000\"
  echo \"  后端 API:         http://${SERVER_IP}:8000\"
  echo \"  API 文档:         http://${SERVER_IP}:8000/docs\"
"

echo ""
echo "部署完成。若需 Nginx 反代 80/443，请参考 deploy/DEPLOY_ALIYUN.md 配置。"
