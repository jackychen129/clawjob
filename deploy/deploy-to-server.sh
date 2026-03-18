#!/bin/bash
# 本机执行：将 ClawJob 代码同步到轻量服务器并启动 Docker 栈
# 用法： SERVER_IP=你的公网IP [SSH_USER=root] [REMOTE_DIR=/opt/clawjob] ./deploy/deploy-to-server.sh
#
# 首次部署前请在本机或服务器上准备好 deploy/.env（从 .env.example 复制并修改域名、密码、JWT_SECRET、Google OAuth 等）

set -e
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_DIR="$(dirname "$0")"
cd "$REPO_ROOT"

# 从 deploy/.deploy_env 读取 SERVER_IP、可选 SSL_DOMAIN/DEPLOY_DOMAIN（用于域名访问时 API/CORS）
if [ -f "${DEPLOY_DIR}/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "${DEPLOY_DIR}/.deploy_env"
  set +a
fi
export DEPLOY_SSH_KEY
export DEPLOY_SSH_PASSWORD
DOMAIN="${SSL_DOMAIN:-$DEPLOY_DOMAIN}"

SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

if [ -z "$SERVER_IP" ]; then
  echo "请设置服务器公网 IP，例如："
  echo "  SERVER_IP=47.74.xxx.xxx ./deploy/deploy-to-server.sh"
  echo ""
  echo "可选：SSH_USER=root REMOTE_DIR=/opt/clawjob"
  echo "解决 Permission denied (publickey)：见下方 SSH_KEY / SSH_PASSWORD 说明"
  exit 1
fi

# 默认使用 newclawjobkey.pem（未设置 DEPLOY_SSH_KEY 且该文件存在时）
if [ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ]; then
  export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
fi

# 解决 Permission denied (publickey)：支持指定密钥或密码，否则用本机默认 SSH
SSH_OPTS=""
RSYNC_RSH=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass。请先安装：brew install sshpass 或 sudo apt install sshpass"
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
  SSH_OPTS="-i $DEPLOY_SSH_KEY -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
elif [ -f "${DEPLOY_DIR}/.ssh/id_ed25519" ]; then
  SSH_OPTS="-i ${DEPLOY_DIR}/.ssh/id_ed25519 -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
elif [ -f "${DEPLOY_DIR}/.ssh/id_rsa" ]; then
  SSH_OPTS="-i ${DEPLOY_DIR}/.ssh/id_rsa -o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
else
  SSH_OPTS="-o StrictHostKeyChecking=accept-new"
  RSYNC_RSH="ssh $SSH_OPTS"
  SSH_CMD="ssh $SSH_OPTS"
fi

# 部署前 SSH 预检
if ! $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" &>/dev/null; then
  echo "错误：无法 SSH 登录 ${SSH_USER}@${SERVER_IP}。请配置 DEPLOY_SSH_PASSWORD 或密钥，见 deploy/README_DEPLOY_ALL.md"
  exit 1
fi

# 避免 SSH Host key verification failed
if ! ssh-keygen -F "$SERVER_IP" &>/dev/null 2>&1; then
  echo ">>> 将 ${SERVER_IP} 加入 known_hosts..."
  ssh-keyscan -H "$SERVER_IP" 2>/dev/null >> ~/.ssh/known_hosts 2>/dev/null || true
fi

echo ">>> 目标: ${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}"
echo ">>> 同步代码（排除 node_modules、.git、__pycache__、frontend/dist；保留服务器 deploy/.env）..."
rsync -avz --delete \
  --exclude 'node_modules' \
  --exclude '.git' \
  --exclude '**/__pycache__' \
  --exclude 'frontend/dist' \
  --exclude 'backend/.pytest_cache' \
  --exclude '*.pyc' \
  --exclude 'deploy/.env' \
  ${RSYNC_RSH:+-e "$RSYNC_RSH"} \
  "$REPO_ROOT/" "${SSH_USER}@${SERVER_IP}:${REMOTE_DIR}/"

echo ">>> 在服务器上检查 .env 并启动 Docker..."
# 有域名时强制重建前端，确保 VITE_API_BASE_URL 为 https://api.$DOMAIN，域名访问才能拿到数据
export FORCE_REBUILD_FRONTEND="${FORCE_REBUILD_FRONTEND:-$([ -n "$DOMAIN" ] && echo 1 || echo 0)}"
# 将 SERVER_IP 注入到远程脚本（用于修补 .env）
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "export FORCE_REBUILD_FRONTEND='${FORCE_REBUILD_FRONTEND}'; export DOMAIN='${DOMAIN}'; set -e
  cd ${REMOTE_DIR}/deploy
  if [ ! -f .env ]; then
    cp .env.example .env
    echo ''
    echo '已在服务器上创建 deploy/.env，请先编辑并填入真实配置后重新运行本脚本：'
    echo \"  ssh ${SSH_USER}@${SERVER_IP} 'vim ${REMOTE_DIR}/deploy/.env'\"
    echo '  必改：VITE_API_BASE_URL、FRONTEND_URL、CORS_ORIGINS、POSTGRES_PASSWORD、DATABASE_URL、REDIS_PASSWORD、REDIS_URL、JWT_SECRET'
    echo ''
    exit 1
  fi
  SIP='${SERVER_IP}'
  if [ -n \"\$DOMAIN\" ]; then
    API_URL=\"https://api.\$DOMAIN\"
    CORS_VAL=\"https://app.\$DOMAIN,https://\$DOMAIN,https://www.\$DOMAIN\"
    FRONT_VAL=\"https://app.\$DOMAIN\"
    SKILL_VAL=\"https://\$DOMAIN/skill\"
  else
    API_URL=\"http://\$SIP:8000\"
    CORS_VAL=\"http://\$SIP:3000,http://\$SIP\"
    FRONT_VAL=\"http://\$SIP:3000\"
    SKILL_VAL=\"http://\$SIP/skill\"
  fi
  grep -q '^VITE_API_BASE_URL=' .env && sed -i.bak \"s|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=\$API_URL|\" .env || echo \"VITE_API_BASE_URL=\$API_URL\" >> .env
  grep -q '^CORS_ORIGINS=' .env && sed -i.bak \"s|^CORS_ORIGINS=.*|CORS_ORIGINS=\$CORS_VAL|\" .env || echo \"CORS_ORIGINS=\$CORS_VAL\" >> .env
  grep -q '^FRONTEND_URL=' .env && sed -i.bak \"s|^FRONTEND_URL=.*|FRONTEND_URL=\$FRONT_VAL|\" .env || echo \"FRONTEND_URL=\$FRONT_VAL\" >> .env
  grep -q '^VITE_SKILL_VIEW_URL=' .env && sed -i.bak \"s|^VITE_SKILL_VIEW_URL=.*|VITE_SKILL_VIEW_URL=\$SKILL_VAL|\" .env || echo \"VITE_SKILL_VIEW_URL=\$SKILL_VAL\" >> .env
  if [ \"\$FORCE_REBUILD_FRONTEND\" = \"1\" ]; then echo '强制重建前端镜像（无缓存）...'; docker compose -f docker-compose.prod.yml --env-file .env build --no-cache frontend; fi
  echo '启动 Docker Compose（已按 SERVER_IP 修补 VITE_API_BASE_URL / CORS_ORIGINS）...'
  docker compose -f docker-compose.prod.yml --env-file .env up -d --build
  echo ''
  echo '等待服务就绪（约 30 秒）...'
  sleep 30
  docker compose -f docker-compose.prod.yml ps
  echo ''
  echo '>>> 数据库表由后端启动时自动创建。'
  if [ -n \"\$DOMAIN\" ]; then
    echo '>>> 域名访问（请确保 Nginx 已反代 api.'\"\$DOMAIN\"'、app.'\"\$DOMAIN\"' 与根域 \"'\"\$DOMAIN\"'\"）：'
    echo \"  前端: https://app.\${DOMAIN}  根域: https://\${DOMAIN}（与 app 共用同一前端，数据一致）  后端 API: https://api.\${DOMAIN}  文档: https://api.\${DOMAIN}/docs\"
    echo '>>> 若根域当前指向静态站导致数据为 0，请更新 Nginx 配置：deploy/nginx/clawjob-ssl.conf 中根域已改为反代到前端，在服务器执行：'
    echo \"     sed 's/{{DOMAIN}}/\${DOMAIN}/g' ${REMOTE_DIR}/deploy/nginx/clawjob-ssl.conf | sudo tee /etc/nginx/conf.d/clawjob.conf && sudo nginx -t && sudo systemctl reload nginx\"
  fi
  echo '>>> IP 访问：'
  echo \"  前端: http://${SERVER_IP}:3000  后端 API: http://${SERVER_IP}:8000  文档: http://${SERVER_IP}:8000/docs\"
"

echo ""
echo "部署完成。若需 Nginx 反代 80/443，请参考 deploy/DEPLOY_ALIYUN.md 配置。"
echo "校验前端样式是否生效: CLAWJOB_FRONTEND_URL=http://${SERVER_IP}:3000 python3 deploy/verify-frontend-styles.py"
