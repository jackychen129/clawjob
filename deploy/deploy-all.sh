#!/bin/bash
# 一键部署：官网（clawjob-website）+ ClawJob 应用（任务大厅+后端）到轻量服务器
# 用法：在 jasonproject 父目录执行 SERVER_IP=43.99.97.240 ./clawjob/deploy/deploy-all.sh
# 或先写 deploy/.deploy_env 的 SERVER_IP，然后 ./clawjob/deploy/deploy-all.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# 假设 clawjob-website 与 clawjob 同级
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
WEBSITE_ROOT="$PARENT/clawjob-website"

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
  echo "请设置 SERVER_IP，例如: SERVER_IP=43.99.97.240 $0"
  exit 1
fi

# 避免 SSH Host key verification failed：将服务器加入 known_hosts
if [ -n "$SERVER_IP" ]; then
  if ! ssh-keygen -F "$SERVER_IP" &>/dev/null 2>&1; then
    echo ">>> 将 ${SERVER_IP} 加入 known_hosts..."
    ssh-keyscan -H "$SERVER_IP" 2>/dev/null >> ~/.ssh/known_hosts 2>/dev/null || true
  fi
fi

# 与 deploy-to-server.sh 一致的 SSH 认证（密钥或密码）
SSH_USER="${SSH_USER:-root}"
RSYNC_RSH=""
SSH_CMD=""
if [ -n "$DEPLOY_SSH_PASSWORD" ]; then
  if ! command -v sshpass &>/dev/null; then
    echo "错误：已设置 DEPLOY_SSH_PASSWORD，但未安装 sshpass，无法用密码登录。"
    echo "请先安装：  macOS 用 brew install sshpass  |  Linux 用 sudo apt install sshpass"
    exit 1
  fi
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  RSYNC_RSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
elif [ -n "$DEPLOY_SSH_KEY" ]; then
  # 展开 ~ 并检查密钥文件存在
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  if [ ! -f "$DEPLOY_SSH_KEY" ]; then
    echo "错误：DEPLOY_SSH_KEY 指向的文件不存在: $DEPLOY_SSH_KEY"
    echo "请检查 deploy/.deploy_env 中 DEPLOY_SSH_KEY 路径（如 ~/Downloads/cursor.pem 或 ~/Download/cursor.pem）"
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
  # 使用本机默认 SSH 身份（~/.ssh/id_ed25519 或 ~/.ssh/id_rsa 等）
  RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new"
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new"
fi

# 部署前 SSH 预检：避免构建完才发现传不上去
echo ">>> 检查 SSH 连接 ${SSH_USER}@${SERVER_IP} ..."
if ! $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" &>/dev/null; then
  echo ""
  echo "错误：无法通过 SSH 登录服务器。正在运行诊断脚本查看具体原因..."
  echo ""
  if [ -x "$SCRIPT_DIR/check-ssh.sh" ]; then
    "$SCRIPT_DIR/check-ssh.sh" || true
  else
    $SSH_CMD -o BatchMode=yes -o ConnectTimeout=10 "${SSH_USER}@${SERVER_IP}" "echo ok" 2>&1 || true
  fi
  echo ""
  echo "请任选一种方式配置认证后重试："
  echo "  1) 密码：export DEPLOY_SSH_PASSWORD='你的root密码'（需安装 sshpass）"
  echo "  2) 密钥：在 deploy/.deploy_env 中设置 DEPLOY_SSH_KEY=你的私钥路径，或执行 export DEPLOY_SSH_KEY=~/.ssh/id_ed25519"
  echo "  3) 项目内密钥：运行 ./deploy/setup-ssh-once.sh，按提示把公钥加到服务器后再部署"
  echo "  4) 本机默认密钥：确保 ~/.ssh 下私钥对应的公钥已加入服务器 authorized_keys"
  echo "详见 deploy/README_DEPLOY_ALL.md 第二节「解决 Permission denied」"
  echo ""
  exit 1
fi
echo ">>> SSH 连接正常，开始部署..."
echo ""

echo "========== 1. 部署官网 (clawjob-website) =========="
if [ ! -d "$WEBSITE_ROOT" ]; then
  echo "未找到 $WEBSITE_ROOT，跳过官网部署。"
else
  cd "$WEBSITE_ROOT"
  # 官网「体验任务大厅」按钮指向本机部署的 ClawJob 应用
  export VITE_TASK_HALL_URL="http://${SERVER_IP}:3000"
  npm run build
  rsync -avz --delete ${RSYNC_RSH:+-e "$RSYNC_RSH"} dist/ "${SSH_USER}@${SERVER_IP}:/var/www/clawjob-website/"
  echo "官网已上传到 /var/www/clawjob-website/（任务大厅链接: $VITE_TASK_HALL_URL）"
  # 若有 clawjob-skill（与 clawjob 同级），一并同步到官网目录供访问
  if [ -d "$PARENT/clawjob-skill" ]; then
    echo ">>> 同步 ClawSkill 到官网 /skill/ ..."
    $SSH_CMD "${SSH_USER}@${SERVER_IP}" "mkdir -p /var/www/clawjob-website/skill"
    rsync -avz ${RSYNC_RSH:+-e "$RSYNC_RSH"} "$PARENT/clawjob-skill/" "${SSH_USER}@${SERVER_IP}:/var/www/clawjob-website/skill/"
    echo "ClawSkill 已上传到 /var/www/clawjob-website/skill/"
  fi
fi

echo ""
echo "========== 2. 部署 ClawJob 应用（任务大厅+后端） =========="
cd "$CLAWJOB_ROOT"
"$SCRIPT_DIR/deploy-to-server.sh"

echo ""
echo "========== 3. 等待后端就绪后初始化数据库（首次必做） =========="
sleep 20
$SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec -T backend sh -c 'PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\"' 2>/dev/null" && echo "数据库初始化 OK" || {
  echo "（若失败：等 1 分钟后手动执行）"
  echo "  ssh root@${SERVER_IP} 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c \"PYTHONPATH=. python3 -c \\\"from app.database.relational_db import init_db; init_db(); print(\\\\\\\"OK\\\\\\\")\\\"\"'"
}

if [ -n "$RUN_SEED_DEMO" ]; then
  echo ""
  echo "========== 3.1 填充演示数据（RUN_SEED_DEMO=1） =========="
  $SSH_CMD "${SSH_USER}@${SERVER_IP}" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec -T backend sh -c 'cd /app && PYTHONPATH=. python3 scripts/seed_demo_data.py'" && echo "演示数据 OK" || echo "（种子脚本执行失败或已存在数据，可忽略）"
fi

echo ""
echo "========== 部署完成 =========="
echo "  官网:        http://${SERVER_IP}/"
echo "  任务大厅:    http://${SERVER_IP}:3000"
echo "  后端 API:    http://${SERVER_IP}:8000"
echo "  验证:        python3 $SCRIPT_DIR/verify-deployed.py http://${SERVER_IP}:8000"
