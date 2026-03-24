#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$CLAWJOB_ROOT"

[ -f "$SCRIPT_DIR/.deploy_env" ] && set -a && . "$SCRIPT_DIR/.deploy_env" && set +a
[ -f "$SCRIPT_DIR/ssh_key_fallback.sh" ] && . "$SCRIPT_DIR/ssh_key_fallback.sh"

SERVER_IP="${SERVER_IP:-43.99.97.240}"
SSH_USER="${SSH_USER:-root}"
REMOTE_DIR="${REMOTE_DIR:-/opt/clawjob}"

KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
SSH_KEEPALIVE="-o ServerAliveInterval=60 -o ServerAliveCountMax=10"
if [ -n "$DEPLOY_SSH_KEY" ] && [ -f "$KEY" ]; then
  SSH_CMD="ssh -i $KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $SSH_KEEPALIVE"
else
  SSH_CMD="ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 $SSH_KEEPALIVE"
fi
TARGET="${SSH_USER}@${SERVER_IP}"

echo "========== 任务大厅诊断（目标 ${TARGET}）=========="
echo ""

# NOTE: translated comment in English.
echo "1) 外网探测 ${SERVER_IP}:3000"
CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://${SERVER_IP}:3000/" 2>/dev/null || echo "000")
if [ "$CODE" = "200" ]; then
  echo "   外网 3000: HTTP 200 — 任务大厅应可访问"
  echo "   请用浏览器打开: http://${SERVER_IP}:3000"
  exit 0
fi
echo "   外网 3000: $CODE（非 200 或超时）"
echo ""

# NOTE: translated comment in English.
echo "2) 服务器本机状态（需 SSH）"
if ! $SSH_CMD "$TARGET" "echo ok" &>/dev/null; then
  echo "   SSH 失败，无法继续。请检查："
  echo "   - 本机能否 SSH 到 ${SERVER_IP}（bash deploy/check-ssh.sh）"
  echo "   - 阿里云防火墙是否放行 TCP 22"
  exit 1
fi

$SSH_CMD "$TARGET" "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""

LOCAL_CODE=$($SSH_CMD "$TARGET" "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 http://127.0.0.1:3000/ 2>/dev/null" || echo "000")
echo "   本机 127.0.0.1:3000 → HTTP $LOCAL_CODE"
echo ""

if [ "$LOCAL_CODE" = "200" ]; then
  echo "========== 结论 =========="
  echo "服务器本机 3000 正常，外网打不开多半是防火墙未放行。"
  echo ""
  echo "请到 阿里云轻量应用服务器控制台 → 该实例 → 防火墙 → 添加入站规则："
  echo "  端口: TCP 3000"
  echo "  来源: 0.0.0.0/0"
  echo ""
  echo "保存后用浏览器访问: http://${SERVER_IP}:3000"
  exit 0
fi

# NOTE: translated comment in English.
echo "3) 修补 .env 并启动任务大厅（frontend + backend）..."
$SSH_CMD "$TARGET" "set -e
  cd ${REMOTE_DIR}/deploy
  [ ! -f .env ] && cp .env.example .env
  SIP='${SERVER_IP}'
  grep -q '^VITE_API_BASE_URL=' .env && sed -i.bak \"s|^VITE_API_BASE_URL=.*|VITE_API_BASE_URL=http://\$SIP:8000|\" .env || echo \"VITE_API_BASE_URL=http://\$SIP:8000\" >> .env
  grep -q '^CORS_ORIGINS=' .env && sed -i.bak \"s|^CORS_ORIGINS=.*|CORS_ORIGINS=http://\$SIP:3000,http://\$SIP|\" .env || echo \"CORS_ORIGINS=http://\$SIP:3000,http://\$SIP\" >> .env
  grep -q '^FRONTEND_URL=' .env && sed -i.bak \"s|^FRONTEND_URL=.*|FRONTEND_URL=http://\$SIP:3000|\" .env || echo \"FRONTEND_URL=http://\$SIP:3000\" >> .env
  docker compose -f docker-compose.prod.yml --env-file .env up -d --build frontend backend
"
echo "   等待 40 秒..."
sleep 40
echo ""

# NOTE: translated comment in English.
LOCAL_CODE2=$($SSH_CMD "$TARGET" "curl -s -o /dev/null -w '%{http_code}' --connect-timeout 5 http://127.0.0.1:3000/ 2>/dev/null" || echo "000")
$SSH_CMD "$TARGET" "docker ps -a --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'"
echo ""
echo "   本机 127.0.0.1:3000 → HTTP $LOCAL_CODE2"
echo ""

echo "========== 结论与下一步 =========="
if [ "$LOCAL_CODE2" = "200" ]; then
  echo "服务器上任务大厅已就绪。若外网仍打不开，请到 阿里云轻量控制台 → 该实例 → 防火墙 → 添加入站规则：TCP 3000，来源 0.0.0.0/0。"
else
  echo "本机 3000 仍非 200，请查看上方 docker 状态与日志："
  echo "  ssh ${TARGET} 'docker logs clawjob-frontend --tail 30'"
fi
echo ""
echo "任务大厅地址: http://${SERVER_IP}:3000"
echo "完成。"
