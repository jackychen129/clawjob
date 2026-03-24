#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.

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

SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

# NOTE: translated comment in English.
SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-465}"
SMTP_USER="${SMTP_USER:-}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"
SMTP_FROM="${SMTP_FROM:-$SMTP_USER}"

if [ -z "$SMTP_USER" ] || [ -z "$SMTP_PASSWORD" ]; then
  echo "请设置环境变量 SMTP_USER 和 SMTP_PASSWORD，例如："
  echo "  SMTP_USER=openclawjob@gmail.com SMTP_PASSWORD=你的16位应用专用密码 bash deploy/update-smtp-on-server.sh"
  echo "Gmail 应用专用密码（无空格）：在 Google 账号 → 安全性 → 两步验证 → 应用专用密码 生成。"
  exit 1
fi

if [ -z "$SERVER_IP" ]; then
  echo "请先在 deploy/.deploy_env 中设置 SERVER_IP"
  exit 1
fi

# NOTE: translated comment in English.
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
echo ">>> 更新线上 SMTP 配置并重启 backend..."
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "bash -s" "$ENV_FILE" "$SMTP_HOST" "$SMTP_PORT" "$SMTP_USER" "$SMTP_PASSWORD" "$SMTP_FROM" << 'REMOTE'
ENV_FILE="$1"
SMTP_HOST="$2"
SMTP_PORT="$3"
SMTP_USER="$4"
SMTP_PASSWORD="$5"
SMTP_FROM="$6"
cd "$(dirname "$ENV_FILE")" || exit 1
if [ ! -f .env ]; then
  echo "错误：.env 不存在"
  exit 1
fi
set_var() {
  var="$1"
  val="$2"
  if grep -q "^${var}=" .env 2>/dev/null; then
    sed -i.bak "s|^${var}=.*|${var}=${val}|" .env
  else
    echo "${var}=${val}" >> .env
  fi
}
set_var SMTP_HOST "$SMTP_HOST"
set_var SMTP_PORT "$SMTP_PORT"
set_var SMTP_USER "$SMTP_USER"
set_var SMTP_PASSWORD "$SMTP_PASSWORD"
set_var SMTP_FROM "$SMTP_FROM"
echo ">>> .env 中 SMTP_* 已更新"
REMOTE

echo ">>> 重启 backend..."
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd ${REMOTE_DIR}/deploy && docker compose -f docker-compose.prod.yml --env-file .env up -d --force-recreate backend"

echo ""
echo "========== 完成 =========="
echo "  SMTP 已设为: $SMTP_USER (Gmail 端口 465)。可注册测试验证码邮件。"
echo "  若未收到邮件，可执行: ./deploy/fetch-backend-logs.sh 500 smtp"
echo ""
