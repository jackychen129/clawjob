#!/bin/bash
# 仅部署官网（clawjob-website）到服务器，并注入当前 SERVER_IP 对应的任务大厅链接；同步 skill 到 /skill/。
# 用法：cd /path/to/clawjob && bash deploy/deploy-website-only.sh
# 依赖：deploy/.deploy_env 中 SERVER_IP、SSH 认证；与 clawjob 同级的 clawjob-website 目录。

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
if [ -n "$WEBSITE_ROOT" ] && [ -d "$WEBSITE_ROOT" ]; then
  :
elif [ -d "$PARENT/clawjob-website" ]; then
  WEBSITE_ROOT="$PARENT/clawjob-website"
elif [ -d "$CLAWJOB_ROOT/clawjob-website" ]; then
  WEBSITE_ROOT="$CLAWJOB_ROOT/clawjob-website"
else
  WEBSITE_ROOT=""
fi

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
export SERVER_IP
export DEPLOY_SSH_KEY
export DEPLOY_SSH_PASSWORD
export SSH_USER

if [ -z "$SERVER_IP" ]; then
  echo "请设置 SERVER_IP，或在 deploy/.deploy_env 中配置。"
  exit 1
fi

if [ -z "$WEBSITE_ROOT" ] || [ ! -d "$WEBSITE_ROOT" ]; then
  echo "未找到 clawjob-website。请将官网放在与 clawjob 同级，或设置 WEBSITE_ROOT=路径。"
  exit 1
fi

# SSH 与 deploy-all.sh 完全一致
SSH_USER="${SSH_USER:-root}"
RSYNC_RSH=""
SSH_CMD=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass。brew install sshpass 或 apt install sshpass"
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
  export DEPLOY_SSH_KEY
  RSYNC_RSH="ssh -i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_ed25519" ]; then
  RSYNC_RSH="ssh -i $SCRIPT_DIR/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
elif [ -f "$SCRIPT_DIR/.ssh/id_rsa" ]; then
  RSYNC_RSH="ssh -i $SCRIPT_DIR/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -i $SCRIPT_DIR/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
else
  RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

# 部署前 SSH 预检
if ! $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" &>/dev/null; then
  echo "错误：无法 SSH 登录 ${SSH_USER}@${SERVER_IP}。请配置密钥或密码，见 deploy/README_DEPLOY_ALL.md"
  exit 1
fi

# 任务大厅链接：优先显式配置，否则 SSL 域名，否则 IP
if [ -n "$VITE_TASK_HALL_URL" ]; then
  :
elif [ -n "$SSL_DOMAIN" ]; then
  export VITE_TASK_HALL_URL="https://app.${SSL_DOMAIN}"
else
  export VITE_TASK_HALL_URL="http://${SERVER_IP}:3000"
fi
if [ -z "$VITE_STATS_API_URL" ] && [ -n "$SSL_DOMAIN" ]; then
  export VITE_STATS_API_URL="https://api.${SSL_DOMAIN}"
fi
echo "========== 部署官网（任务大厅: $VITE_TASK_HALL_URL  统计 API: ${VITE_STATS_API_URL:-（推导）}）=========="
cd "$WEBSITE_ROOT"
npm run build
rsync -avz --delete ${RSYNC_RSH:+-e "$RSYNC_RSH"} dist/ "${SSH_USER}@${SERVER_IP}:/var/www/clawjob-website/"
echo "官网已上传到 /var/www/clawjob-website/。"

# 同步 clawjob-skill 到官网 /skill/（与 deploy-all 一致）
if [ -n "$PARENT" ] && [ -d "$PARENT/clawjob-skill" ]; then
  echo ">>> 同步 ClawSkill 到官网 /skill/ ..."
  $SSH_CMD "${SSH_USER}@${SERVER_IP}" "mkdir -p /var/www/clawjob-website/skill"
  rsync -avz ${RSYNC_RSH:+-e "$RSYNC_RSH"} "$PARENT/clawjob-skill/" "${SSH_USER}@${SERVER_IP}:/var/www/clawjob-website/skill/"
  echo "ClawSkill 已上传到 /var/www/clawjob-website/skill/"
fi

echo "体验任务大厅 → $VITE_TASK_HALL_URL  官网 Skill → http://${SERVER_IP}/skill/"
