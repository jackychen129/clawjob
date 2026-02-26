#!/bin/bash
# 本机执行：检查并修复 clawjob 线上前后端，并跑完全部 API 验证。
# 依赖：能 SSH root@SERVER_IP（使用 deploy/.deploy_env 或 newclawjobkey.pem）。
# 用法：cd /path/to/clawjob && bash deploy/check-and-fix-online.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
[ -z "$DEPLOY_SSH_KEY" ] && [ -f "$HOME/Downloads/newclawjobkey.pem" ] && export DEPLOY_SSH_KEY="$HOME/Downloads/newclawjobkey.pem"
SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"

KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
if [ -n "$DEPLOY_SSH_KEY" ] && [ -f "$KEY" ]; then
  SSH_CMD="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
else
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15"
fi
TARGET="${SSH_USER}@${SERVER_IP}"

# 先做外网可达性检查（不依赖 SSH）
echo "========== 外网可达性（本机 -> ${SERVER_IP}） =========="
curl -s -o /dev/null -w "3000: %{http_code}\n" --connect-timeout 5 "http://${SERVER_IP}:3000/" 2>/dev/null || echo "3000: 超时或失败"
curl -s -o /dev/null -w "8000/health: %{http_code}\n" --connect-timeout 5 "http://${SERVER_IP}:8000/health" 2>/dev/null || echo "8000/health: 超时或失败"
echo ""

echo "========== 0. 服务器 .env 关键配置 =========="
$SSH_CMD "$TARGET" "grep -E '^VITE_API_BASE_URL=|^CORS_ORIGINS=|^FRONTEND_URL=' /opt/clawjob/deploy/.env 2>/dev/null || echo '(无 .env 或无上述键)'" 2>/dev/null || echo "SSH 跳过（超时或未配置密钥）"
echo ""

echo "========== 1. 服务器容器与端口 =========="
$SSH_CMD "$TARGET" "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null || { echo "SSH 失败或超时，仅继续外网验证"; }
echo ""

echo "========== 2. 服务器本机 3000/8000 =========="
$SSH_CMD "$TARGET" "curl -s -o /dev/null -w '3000: %{http_code}\n' http://127.0.0.1:3000/ ; curl -s -o /dev/null -w '8000/health: %{http_code}\n' http://127.0.0.1:8000/health" 2>/dev/null || echo "(需 SSH 连通)"
echo ""

echo "========== 3. 前端日志 (tail 20) =========="
$SSH_CMD "$TARGET" "docker logs clawjob-frontend --tail 20 2>&1" 2>/dev/null || echo "(需 SSH 连通)"
echo ""

echo "========== 4. 后端日志 (tail 15) =========="
$SSH_CMD "$TARGET" "docker logs clawjob-backend --tail 15 2>&1" 2>/dev/null || echo "(需 SSH 连通)"
echo ""

# 若 frontend 或 backend 未 Up，启动并等待（仅当 SSH 可用时）
FRONT_UP=$($SSH_CMD "$TARGET" "docker inspect -f '{{.State.Running}}' clawjob-frontend 2>/dev/null" || echo "false")
BACK_UP=$($SSH_CMD "$TARGET" "docker inspect -f '{{.State.Running}}' clawjob-backend 2>/dev/null" || echo "false")
if [ "$FRONT_UP" = "true" ] && [ "$BACK_UP" = "true" ]; then
  echo "========== 5. 容器已在运行，跳过启动 =========="
else
  echo "========== 5. 启动/重建容器 =========="
  if $SSH_CMD "$TARGET" "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml up -d --build" 2>/dev/null; then
    echo "等待 60 秒..."
    sleep 60
    $SSH_CMD "$TARGET" "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'" 2>/dev/null || true
  else
    echo "SSH 不可用，请本机执行: ./deploy/fix-task-hall.sh"
  fi
  echo ""
fi

echo "========== 6. 线上 API 全流程验证 =========="
python3 "$SCRIPT_DIR/verify-deployed.py" "http://${SERVER_IP}:8000" 2>&1 || true
echo ""

echo "========== 完成 =========="
echo "任务大厅: http://${SERVER_IP}:3000"
echo "后端 API: http://${SERVER_IP}:8000"
echo "若 3000 外网超时：1) 阿里云防火墙放行 TCP 3000  2) 本机执行 ./deploy/fix-task-hall.sh 启动容器"
