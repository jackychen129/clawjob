#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PARENT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# NOTE: translated comment in English.
export DEPLOY_SSH_KEY="$HOME/Downloads/cursor.pem"
if [ ! -f "$DEPLOY_SSH_KEY" ]; then
  echo "错误：密钥文件不存在: $DEPLOY_SSH_KEY"
  exit 1
fi

# NOTE: translated comment in English.
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
