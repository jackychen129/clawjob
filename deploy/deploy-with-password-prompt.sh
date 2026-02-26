#!/bin/bash
# 在本机运行：提示输入 root 密码后执行一键部署（密码不落盘，仅本次有效）
# 用法：./deploy/deploy-with-password-prompt.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

if ! command -v sshpass &>/dev/null; then
  echo "请先安装 sshpass："
  echo "  macOS:   brew install sshpass"
  echo "  Linux:   sudo apt install sshpass"
  exit 1
fi

if [ -z "$SERVER_IP" ] && [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
SERVER_IP="${SERVER_IP:-43.99.97.240}"

echo ">>> 将使用密码登录 root@${SERVER_IP} 进行部署（密码不会保存）。"
echo -n "请输入 root 密码: "
read -rs DEPLOY_SSH_PASSWORD
echo ""
if [ -z "$DEPLOY_SSH_PASSWORD" ]; then
  echo "未输入密码，退出。"
  exit 1
fi

export DEPLOY_SSH_PASSWORD
export SERVER_IP
"$SCRIPT_DIR/deploy-all.sh"
