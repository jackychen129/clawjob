#!/bin/bash
# 本机执行：SSH 到服务器启动任务大厅（frontend）及依赖，并提示放行 3000 端口。
# 依赖：能 SSH root@SERVER_IP（使用 newclawjobkey.pem 或 .deploy_env 中的密钥）。
# 用法：./deploy/fix-task-hall.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
# 默认使用 newclawjobkey.pem
if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"

if [ -z "$SERVER_IP" ]; then
  echo "请设置 SERVER_IP 或配置 deploy/.deploy_env"
  exit 1
fi

SSH_CMD=""
if [ -n "$DEPLOY_SSH_KEY" ]; then
  KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  [ -f "$KEY" ] && SSH_CMD="ssh -i $KEY -o StrictHostKeyChecking=accept-new"
fi
[ -z "$SSH_CMD" ] && SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"

echo ">>> 连接 ${SSH_USER}@${SERVER_IP} 并启动任务大厅及依赖..."
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo ">>> 等待约 30 秒后检查容器状态..."
sleep 30
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""
echo "若 frontend 为 Up，本机访问任务大厅："
echo "  http://${SERVER_IP}:3000"
echo ""
echo "若外网仍访问不了，请到 阿里云轻量控制台 → 该实例 → 防火墙 → 添加入站规则：TCP 3000，来源 0.0.0.0/0。"
echo "完成。"
