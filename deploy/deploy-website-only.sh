#!/bin/bash
# 仅部署官网（clawjob-website）到服务器，并注入当前 SERVER_IP 对应的任务大厅链接。
# 用于：更换服务器 IP 后只更新官网「体验任务大厅」跳转，无需完整 deploy-all。
# 用法：cd /path/to/clawjob && bash deploy/deploy-website-only.sh
# 依赖：deploy/.deploy_env 中 SERVER_IP、DEPLOY_SSH_KEY；与 clawjob 同级的 clawjob-website 目录。

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
WEBSITE_ROOT="$PARENT/clawjob-website"

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi

if [ -z "$SERVER_IP" ]; then
  echo "请设置 SERVER_IP，或在 deploy/.deploy_env 中配置。"
  exit 1
fi

if [ ! -d "$WEBSITE_ROOT" ]; then
  echo "未找到 $WEBSITE_ROOT，请将 clawjob-website 放在与 clawjob 同级目录。"
  exit 1
fi

# SSH 与 deploy-all 一致
export DEPLOY_SSH_KEY
if [ -n "$DEPLOY_SSH_KEY" ] && [ -f "${DEPLOY_SSH_KEY/#\~/$HOME}" ]; then
  RSYNC_RSH="ssh -i ${DEPLOY_SSH_KEY/#\~/$HOME} -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -i ${DEPLOY_SSH_KEY/#\~/$HOME} -o StrictHostKeyChecking=accept-new"
else
  RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

SSH_USER="${SSH_USER:-root}"
export VITE_TASK_HALL_URL="http://${SERVER_IP}:3000"

echo "========== 部署官网（任务大厅链接: $VITE_TASK_HALL_URL）=========="
cd "$WEBSITE_ROOT"
npm run build
rsync -avz --delete ${RSYNC_RSH:+-e "$RSYNC_RSH"} dist/ "${SSH_USER}@${SERVER_IP}:/var/www/clawjob-website/"
echo "官网已上传到 /var/www/clawjob-website/。"
echo "体验任务大厅 → $VITE_TASK_HALL_URL"
