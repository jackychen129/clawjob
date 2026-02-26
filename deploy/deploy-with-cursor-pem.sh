#!/bin/bash
# 使用 ~/Downloads/cursor.pem 密钥执行完整部署（官网 + ClawJob）
# 用法：在 jasonproject 目录下执行 ./clawjob/deploy/deploy-with-cursor-pem.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# 使用 Downloads 下的 cursor.pem
export DEPLOY_SSH_KEY="$HOME/Downloads/cursor.pem"
if [ ! -f "$DEPLOY_SSH_KEY" ]; then
  echo "错误：密钥文件不存在: $DEPLOY_SSH_KEY"
  exit 1
fi

# 读取 .deploy_env 中的 SERVER_IP（若有）
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
export SERVER_IP="${SERVER_IP:-43.99.97.240}"

echo ">>> 使用密钥: $DEPLOY_SSH_KEY"
echo ">>> 目标服务器: ${SERVER_IP}"
echo ""

cd "$PARENT"
exec "$SCRIPT_DIR/deploy-all.sh"
