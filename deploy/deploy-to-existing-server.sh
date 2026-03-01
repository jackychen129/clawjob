#!/bin/bash
# 在已有实例（如日本）上部署：官网 + ClawJob 前端 + 后端。会先准备 Docker/Nginx/官网目录，再执行 deploy-all。
# 用法：在 jasonproject 下执行（将 SERVER_IP 改为你的日本实例公网 IP）：
#   SERVER_IP=日本实例公网IP bash clawjob/deploy/deploy-to-existing-server.sh
# 或先写入 deploy/.deploy_env 的 SERVER_IP，再：bash clawjob/deploy/deploy-to-existing-server.sh
# 日志会写入 deploy/deploy-run.log；完整验证可再运行：bash clawjob/deploy/verify-all-services.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
DEPLOY_LOG="$SCRIPT_DIR/deploy-run.log"
echo "========== $(date -u +%Y-%m-%dT%H:%M:%SZ) 开始部署 ==========" | tee "$DEPLOY_LOG" 2>/dev/null || true

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
[ -f "$SCRIPT_DIR/ssh_key_fallback.sh" ] && . "$SCRIPT_DIR/ssh_key_fallback.sh"

SERVER_IP="${SERVER_IP:-}"
DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY:-}"
DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
KEY_PATH="${DEPLOY_SSH_KEY:-$HOME/Downloads/newclawjobkey.pem}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"
SSH_USER="${SSH_USER:-root}"

if [ -z "$SERVER_IP" ]; then
  echo "请设置日本实例公网 IP，例如："
  echo "  SERVER_IP=47.74.xxx.xxx bash clawjob/deploy/deploy-to-existing-server.sh"
  echo "或在 clawjob/deploy/.deploy_env 中设置 SERVER_IP=你的日本实例IP"
  exit 1
fi

if [ ! -f "$KEY_PATH" ]; then
  echo "错误：SSH 密钥不存在: $KEY_PATH"
  echo "请设置 DEPLOY_SSH_KEY 或将私钥放到 ~/Downloads/newclawjobkey.pem"
  exit 1
fi

# 写入 .deploy_env 供 deploy-all 使用
cat > "$SCRIPT_DIR/.deploy_env" << EOF
SERVER_IP=$SERVER_IP
DEPLOY_SSH_KEY=$KEY_PATH
EOF
export SERVER_IP
export DEPLOY_SSH_KEY="$KEY_PATH"
SSH_CMD="ssh -i $KEY_PATH -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"

echo "========== 目标: ${SSH_USER}@${SERVER_IP}（日本实例）=========="
echo ""

echo ">>> 检查 SSH..."
if ! $SSH_CMD "${SSH_USER}@${SERVER_IP}" "echo ok" 2>/dev/null; then
  echo "SSH 连接失败，请检查 IP、密钥及安全组 22 端口。"
  exit 1
fi

echo "========== 1. 准备环境（Docker、Nginx、官网目录）=========="
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "bash -s" << 'REMOTE'
set -e
command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)
mkdir -p /var/www/clawjob-website
command -v nginx >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq nginx 2>/dev/null || yum install -y -q nginx 2>/dev/null || true)
if [ -d /etc/nginx/sites-available ]; then
  cat > /etc/nginx/sites-available/default << 'NGX'
server {
    listen 80 default_server;
    root /var/www/clawjob-website;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
NGX
  nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true
elif [ -f /etc/nginx/nginx.conf ]; then
  (grep -q "root.*clawjob-website" /etc/nginx/nginx.conf) || true
fi
echo "OK"
REMOTE

echo ""
echo "========== 2. 部署官网 + ClawJob 前端 + 后端 =========="
cd "$PARENT"
bash clawjob/deploy/deploy-all.sh

echo ""
echo "========== 3. 功能验证 =========="
cd "$CLAWJOB_ROOT"
export CLAWJOB_API_URL="http://${SERVER_IP}:8000"
python3 deploy/verify-deployed.py "http://${SERVER_IP}:8000" || true

echo ""
echo "========== 完成 =========="
echo "  官网:     http://${SERVER_IP}/"
echo "  任务大厅: http://${SERVER_IP}:3000"
echo "  后端 API: http://${SERVER_IP}:8000"
echo "  SSH:      ssh -i $KEY_PATH ${SSH_USER}@${SERVER_IP}"
echo "========== $(date -u +%Y-%m-%dT%H:%M:%SZ) 部署脚本结束 ==========" >> "$DEPLOY_LOG" 2>/dev/null || true
echo "验证所有服务: bash clawjob/deploy/verify-all-services.sh"
