#!/bin/bash
# 一次性执行：生成部署用 SSH 密钥，并提示你把公钥加到服务器，解决 Permission denied (publickey)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KEY_DIR="$SCRIPT_DIR/.ssh"
PUB="$KEY_DIR/id_ed25519.pub"
PRIV="$KEY_DIR/id_ed25519"

mkdir -p "$KEY_DIR"
if [ -f "$PRIV" ]; then
  echo "已存在部署密钥，公钥如下（若已加过服务器可忽略）："
  cat "$PUB"
  exit 0
fi

ssh-keygen -t ed25519 -f "$PRIV" -N "" -C "deploy@clawjob"
chmod 700 "$KEY_DIR"
chmod 600 "$PRIV"

echo ""
echo "========== 请把下面这一行公钥加到服务器 43.99.97.240 =========="
echo ""
cat "$PUB"
echo ""
echo "========== 操作步骤（任选一种） =========="
echo "方式一：用密码登录一次，追加公钥"
echo "  ssh root@43.99.97.240 'mkdir -p ~/.ssh && chmod 700 ~/.ssh'"
echo "  ssh root@43.99.97.240 'echo \"$(cat "$PUB")\" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'"
echo "  （执行上面两条时按提示输入 root 密码）"
echo ""
echo "方式二：在服务器上手动粘贴"
echo "  1. ssh root@43.99.97.240（输入密码登录）"
echo "  2. 执行: mkdir -p ~/.ssh && chmod 700 ~/.ssh"
echo "  3. 执行: echo '上面显示的公钥整行' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
echo ""
echo "完成后直接运行: ./deploy/deploy-all.sh"
