#!/bin/bash
# 诊断 SSH 连接问题：显示当前使用的认证方式、密钥是否存在、以及 SSH 的详细报错。
# 用法：在 clawjob 项目根或 jasonproject 下执行 ./deploy/check-ssh.sh 或 bash deploy/check-ssh.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi

SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"

# 默认使用 newclawjobkey.pem（未设置 DEPLOY_SSH_KEY 且该文件存在时）
if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

echo "========== SSH 诊断 =========="
echo "目标: ${SSH_USER}@${SERVER_IP}"
echo ""

# 与 deploy-all.sh 一致的认证逻辑
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  echo "认证方式: 密码 (DEPLOY_SSH_PASSWORD 已设置)"
  if ! command -v sshpass &>/dev/null; then
    echo "  [问题] 未安装 sshpass，无法用密码登录。请安装: brew install sshpass 或 apt install sshpass"
    exit 1
  fi
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  EXPANDED_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  echo "认证方式: 密钥 DEPLOY_SSH_KEY=$DEPLOY_SSH_KEY"
  echo "  展开路径: $EXPANDED_KEY"
  if [ ! -f "$EXPANDED_KEY" ]; then
    echo "  [问题] 密钥文件不存在。请检查路径，或把私钥放到 deploy/.ssh/id_ed25519 后删除 DEPLOY_SSH_KEY 让脚本自动使用项目内密钥。"
    exit 1
  fi
  SSH_CMD="ssh -i $EXPANDED_KEY -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_ed25519" ]; then
  echo "认证方式: 项目内密钥 deploy/.ssh/id_ed25519"
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_rsa" ]; then
  echo "认证方式: 项目内密钥 deploy/.ssh/id_rsa"
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
else
  echo "认证方式: 本机默认 (~/.ssh/id_ed25519 或 id_rsa)"
  for k in "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
    if [ -f "$k" ]; then
      echo "  找到: $k"
    fi
  done
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

echo ""
echo ">>> 尝试连接（下面会显示 SSH 的详细报错）..."
echo "----------------------------------------"
if $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo OK" 2>&1; then
  echo "----------------------------------------"
  echo "结果: 连接成功"
  exit 0
else
  code=$?
  echo "----------------------------------------"
  echo "结果: 连接失败 (exit $code)"
  echo ""
  echo "常见原因与处理："
  echo "  - timed out / Connection timed out: 连不上 22 端口。请到 阿里云轻量控制台 → 该实例 → 防火墙，添加入站规则放行 TCP 22（来源 0.0.0.0/0 或你的公网 IP）。"
  echo "  - Permission denied (publickey): 服务器上没有你的公钥。请运行 ./deploy/setup-ssh-once.sh 生成密钥并按提示把公钥加到服务器。"
  echo "  - Connection refused: 服务器上 sshd 未运行或未监听 22，请登录控制台/VNC 检查。"
  echo "  - Host key verification failed: 本机执行: ssh-keyscan -H $SERVER_IP >> ~/.ssh/known_hosts"
  exit $code
fi
