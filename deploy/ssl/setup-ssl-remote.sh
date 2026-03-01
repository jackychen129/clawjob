#!/bin/bash
# 本机执行：读取 .deploy_env 中的 SERVER_IP、SSL_DOMAIN，通过 SSH 在服务器上自动配置 Let's Encrypt SSL
# 用法：
#   1. 在 deploy/.deploy_env 中设置 SSL_DOMAIN=你的域名.com（可选 CERTBOT_EMAIL=you@example.com）
#   2. 确保域名 DNS 已指向 SERVER_IP（主域、www、app、api 四条 A 记录）
#   3. 执行：bash deploy/ssl/setup-ssl-remote.sh
# 也可临时覆盖：SSL_DOMAIN=clawjob.com bash deploy/ssl/setup-ssl-remote.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DEPLOY_DIR/.." && pwd)"
cd "$REPO_ROOT"

# 读取 .deploy_env（与 deploy-to-server.sh 一致）
if [ -f "${DEPLOY_DIR}/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${DEPLOY_DIR}/.deploy_env"
  set +a
fi

# 域名：环境变量或 .deploy_env 中的 SSL_DOMAIN / DOMAIN
DOMAIN="${SSL_DOMAIN:-${DOMAIN:-}}"
if [ -z "$DOMAIN" ]; then
  echo "请设置域名。任选一种方式："
  echo "  1) 在 deploy/.deploy_env 中增加：SSL_DOMAIN=你的域名.com"
  echo "  2) 或执行：SSL_DOMAIN=你的域名.com bash $0"
  echo ""
  echo "前置条件：域名 DNS 已指向当前服务器 IP（${SERVER_IP:-未设置 SERVER_IP}），且主域、www、app、api 四条 A 记录已生效。"
  exit 1
fi

if [ -z "$SERVER_IP" ]; then
  echo "请先在 deploy/.deploy_env 中设置 SERVER_IP。"
  exit 1
fi

# SSH 认证（与 deploy-to-server.sh 一致）
export DEPLOY_SSH_KEY
export DEPLOY_SSH_PASSWORD
SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

SSH_CMD=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass。请先安装：brew install sshpass 或 sudo apt install sshpass"
    exit 1
  fi
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  if [ ! -f "$DEPLOY_SSH_KEY" ]; then
    echo "错误：DEPLOY_SSH_KEY 指向的文件不存在: $DEPLOY_SSH_KEY"
    exit 1
  fi
  SSH_CMD="ssh -i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
elif [ -f "${DEPLOY_DIR}/.ssh/id_ed25519" ]; then
  SSH_CMD="ssh -i ${DEPLOY_DIR}/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
elif [ -f "${DEPLOY_DIR}/.ssh/id_rsa" ]; then
  SSH_CMD="ssh -i ${DEPLOY_DIR}/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
else
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

# 预检 SSH
if ! $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" &>/dev/null; then
  echo "错误：无法 SSH 登录 ${SSH_USER}@${SERVER_IP}。请检查 deploy/.deploy_env 中的 DEPLOY_SSH_KEY 或 DEPLOY_SSH_PASSWORD。"
  exit 1
fi

# 同步 deploy 目录（确保服务器上有最新 nginx 配置与 ssl 脚本）
echo ">>> 同步 deploy 目录到服务器..."
rsync -avz --delete \
  -e "$SSH_CMD" \
  "${REPO_ROOT}/deploy/" "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}/deploy/" \
  --exclude '.env' \
  --exclude '.deploy_env' \
  --exclude 'data/' \
  --exclude '.ssh/'

# 在服务器上执行 SSL 配置
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"
echo ""
echo ">>> 在服务器上配置 Let's Encrypt（域名: $DOMAIN）..."
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd ${REMOTE_DIR} && DOMAIN='${DOMAIN}' CERTBOT_EMAIL='${CERTBOT_EMAIL}' bash deploy/ssl/setup-letsencrypt.sh"

echo ""
echo "========== 本机 SSL 自动化完成 =========="
echo "  https://$DOMAIN          → 官网"
echo "  https://app.$DOMAIN     → 任务大厅"
echo "  https://api.$DOMAIN     → 后端 API"
echo ""
echo "建议下一步："
echo "  1. 在服务器上编辑 ${REMOTE_DIR}/deploy/.env，改为："
echo "     VITE_API_BASE_URL=https://api.$DOMAIN"
echo "     FRONTEND_URL=https://app.$DOMAIN"
echo "     CORS_ORIGINS=https://app.$DOMAIN"
echo "  2. 重新构建前端并重启："
echo "     ssh ${SSH_USER}@${SERVER_IP} 'cd ${REMOTE_DIR} && docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend'"
echo "  3. 证书续期已配置为每月自动执行（crontab）。"
echo ""
