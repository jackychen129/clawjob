#!/bin/bash
# 在本机执行：验证线上 API，若失败则按类型自动修复（SSH 到服务器）并重试，直到全部通过或达到最大次数。
# 依赖：deploy/.deploy_env 中 SERVER_IP、DEPLOY_SSH_KEY（或密码）已配置，且本机可 SSH 到服务器。
# 用法：./deploy/verify-and-fix-until-pass.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"

# 与 deploy-all.sh 一致的认证
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
export SERVER_IP
export DEPLOY_SSH_KEY
export DEPLOY_SSH_PASSWORD
export SSH_USER

SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"
# 默认使用 newclawjobkey.pem
if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi
BASE_URL="http://${SERVER_IP}:8000"
MAX_ATTEMPTS=5

SSH_CMD=""
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
if [ -n "$DEPLOY_SSH_PASSWORD" ] && command -v sshpass &>/dev/null; then
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  SSH_CMD="sshpass -e ssh $SSH_OPTS"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  if [ ! -f "$DEPLOY_SSH_KEY" ]; then
    echo "错误：DEPLOY_SSH_KEY 文件不存在: $DEPLOY_SSH_KEY"
    exit 1
  fi
  SSH_CMD="ssh -i $DEPLOY_SSH_KEY $SSH_OPTS"
elif [ -f "$SCRIPT_DIR/.ssh/id_ed25519" ]; then
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_ed25519 $SSH_OPTS"
elif [ -f "$SCRIPT_DIR/.ssh/id_rsa" ]; then
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_rsa $SSH_OPTS"
else
  SSH_CMD="ssh $SSH_OPTS"
fi

run_verify() {
  python3 "$SCRIPT_DIR/verify-deployed.py" "$BASE_URL"
}

apply_fix_timeout() {
  echo ">>> 修复：超时 -> 检查并启动容器（后台构建，避免长时间卡住）..."
  $SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml ps -a; nohup docker compose -f docker-compose.prod.yml up -d --build > /tmp/clawjob-deploy.log 2>&1 & sleep 2; echo 已启动后台构建"
  echo ">>> 等待 90 秒让镜像构建/拉取后再重验..."
  sleep 90
}

apply_fix_500() {
  echo ">>> 修复：500 -> 在服务器上执行 init_db..."
  $SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec -T backend sh -c 'PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\"'"
  echo ">>> 等待 5 秒后重验..."
  sleep 5
}

apply_fix_cors() {
  echo ">>> 修复：CORS/403 -> 确保 CORS_ORIGINS 并重启 backend..."
  local cors_value="http://${SERVER_IP}:3000"
  $SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && (grep -q '^CORS_ORIGINS=' .env || echo 'CORS_ORIGINS=${cors_value}' >> .env) && docker compose -f docker-compose.prod.yml up -d --force-recreate backend"
  echo ">>> 等待 15 秒后重验..."
  sleep 15
}

has_error_type() {
  local type="$1"
  grep -q "$type" "$SCRIPT_DIR/verify-result.txt" 2>/dev/null || true
}

attempt=1
while [ $attempt -le $MAX_ATTEMPTS ]; do
  echo ""
  echo "========== 验证尝试 $attempt/$MAX_ATTEMPTS =========="
  if run_verify; then
    echo ""
    echo "========== 所有检查已通过 =========="
    exit 0
  fi

  if has_error_type "timed out\|timeout"; then
    echo ">>> 先执行服务器端诊断..."
    $SSH_CMD "${SSH_USER}@${SERVER_IP}" "bash -s" < "$SCRIPT_DIR/verify-on-server.sh" 2>/dev/null || true
    apply_fix_timeout
  elif has_error_type "500"; then
    apply_fix_500
  elif has_error_type "CORS\|403\|Origin"; then
    apply_fix_cors
  else
    echo ">>> 无法自动修复当前错误，请查看 deploy/verify-result.txt 和 VERIFY_AND_FIX.md"
    cat "$SCRIPT_DIR/verify-result.txt" 2>/dev/null || true
    exit 1
  fi
  attempt=$((attempt + 1))
done

echo ">>> 已达最大尝试次数 $MAX_ATTEMPTS，仍有失败项。"
cat "$SCRIPT_DIR/verify-result.txt" 2>/dev/null || true
exit 1
