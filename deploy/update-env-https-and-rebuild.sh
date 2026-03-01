#!/bin/bash
# 在 SSL 配置完成后执行：更新服务器 deploy/.env 为 https 域名并重新构建前端
# 用法：在项目根目录执行 bash deploy/update-env-https-and-rebuild.sh
# 依赖：deploy/.deploy_env 中 SERVER_IP 与 SSH 配置（与 deploy-to-server.sh 相同）

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$(dirname "$0")"
cd "$REPO_ROOT"

if [ -f "${DEPLOY_DIR}/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${DEPLOY_DIR}/.deploy_env"
  set +a
fi

DOMAIN="${SSL_DOMAIN:-clawjob.com.cn}"
SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

if [ -z "$SERVER_IP" ]; then
  echo "请先在 deploy/.deploy_env 中设置 SERVER_IP"
  exit 1
fi

# SSH 与 deploy-to-server.sh 一致
export DEPLOY_SSH_KEY DEPLOY_SSH_PASSWORD
SSH_CMD=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  [ -z "$SSHPASS" ] && export SSHPASS="$DEPLOY_SSH_PASSWORD"
  SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  [ -f "$DEPLOY_SSH_KEY" ] && SSH_CMD="ssh -i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
fi
if [ -z "$SSH_CMD" ]; then
  [ -f "${DEPLOY_DIR}/.ssh/id_ed25519" ] && SSH_CMD="ssh -i ${DEPLOY_DIR}/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
  [ -z "$SSH_CMD" ] && [ -f "${DEPLOY_DIR}/.ssh/id_rsa" ] && SSH_CMD="ssh -i ${DEPLOY_DIR}/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
  [ -z "$SSH_CMD" ] && SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

ENV_FILE="${REMOTE_DIR}/deploy/.env"
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "bash -s" "$DOMAIN" "$ENV_FILE" << 'REMOTE'
DOMAIN="$1"
ENV_FILE="$2"
cd "$(dirname "$ENV_FILE")" || exit 1
[ ! -f .env ] && echo "错误：.env 不存在" && exit 1
# 更新或追加三项
for var in VITE_API_BASE_URL FRONTEND_URL CORS_ORIGINS; do
  case "$var" in
    VITE_API_BASE_URL) val="https://api.${DOMAIN}" ;;
    FRONTEND_URL)      val="https://app.${DOMAIN}" ;;
    CORS_ORIGINS)      val="https://app.${DOMAIN}" ;;
    *) val="" ;;
  esac
  [ -z "$val" ] && continue
  if grep -q "^${var}=" .env 2>/dev/null; then
    sed -i "s|^${var}=.*|${var}=${val}|" .env
  else
    echo "${var}=${val}" >> .env
  fi
done
echo ">>> .env 已更新为 https 域名"
REMOTE

echo ">>> 在服务器上重新构建并启动前端..."
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend"

echo ""
echo "========== 完成 =========="
echo "  前端: https://app.${DOMAIN}"
echo "  API:  https://api.${DOMAIN}"
echo ""
