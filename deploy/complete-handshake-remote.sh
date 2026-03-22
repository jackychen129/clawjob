#!/bin/bash
# 在远程服务器上执行：将 Skill 注册「握手」任务（未 completed）批量标记为已完成。
# 依赖与 deploy-to-server.sh 相同：deploy/.deploy_env 中 SERVER_IP、可选 DEPLOY_SSH_KEY / DEPLOY_SSH_PASSWORD
#
# 用法（本机）：
#   bash deploy/complete-handshake-remote.sh

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

if [ -z "$SERVER_IP" ]; then
  echo "请设置 SERVER_IP（deploy/.deploy_env 或环境变量）"
  exit 1
fi

if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

RSYNC_RSH=""
SSH_CMD=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass。"
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

echo ">>> 在服务器 PostgreSQL 中更新握手任务（无需重建 backend 镜像）..."
# 从本机 stdin 传入 SQL，远程 docker exec -i psql 执行
$SSH_CMD "${SSH_USER}@${SERVER_IP}" \
  "docker exec -i clawjob-postgres psql -U agentarena -d agentarena -v ON_ERROR_STOP=1" \
  <<'EOSQL'
UPDATE tasks
SET
  status = 'completed',
  completed_at = COALESCE(completed_at, NOW()),
  submitted_at = COALESCE(submitted_at, NOW())
WHERE status IS DISTINCT FROM 'completed'
  AND (
    title ILIKE '%handshake%'
    OR title ILIKE '%握手%'
    OR description ILIKE '%握手任务%'
  );
SELECT id, title, status, completed_at
FROM tasks
WHERE title ILIKE '%handshake%' OR title ILIKE '%握手%' OR description ILIKE '%握手任务%'
ORDER BY id DESC
LIMIT 20;
EOSQL

echo ">>> 完成。"
