#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
export SERVER_IP
export DEPLOY_SSH_KEY
export SSH_USER
if [ -z "$SERVER_IP" ]; then
  echo "请在 deploy/.deploy_env 中设置 SERVER_IP，或执行: SERVER_IP=你的服务器IP $0"
  exit 1
fi
SSH_USER="${SSH_USER:-root}"
if [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  [ -f "$DEPLOY_SSH_KEY" ] || { echo "DEPLOY_SSH_KEY 文件不存在: $DEPLOY_SSH_KEY"; exit 1; }
  SSH_CMD="ssh -i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_ed25519" ]; then
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_rsa" ]; then
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
else
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi
TAIL="${1:-500}"
GREP="${2:-}"
echo ">>> 拉取 backend 最近 ${TAIL} 行日志 (${SSH_USER}@${SERVER_IP}) ..."
if [ "$GREP" = "smtp" ] || [ "$GREP" = "mail" ] || [ "$GREP" = "verification" ]; then
  $SSH_CMD -o ConnectTimeout=12 "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml logs backend --tail $TAIL 2>&1" | grep -iE "SMTP|smtp|verification|mail|邮件|sendmail|Failed to send|not configured" || true
else
  $SSH_CMD -o ConnectTimeout=12 "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml logs backend --tail $TAIL 2>&1"
fi
