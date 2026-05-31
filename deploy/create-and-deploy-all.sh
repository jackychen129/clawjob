#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
LOG="$SCRIPT_DIR/create-deploy.log"
exec > >(tee -a "$LOG") 2>&1

KEY_PATH="${LOCAL_SSH_KEY_PATH:-$HOME/Downloads/newclawjobkey.pem}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"
echo "========== $(date '+%Y-%m-%d %H:%M:%S') 创建并部署 =========="
echo "密钥: $KEY_PATH"
echo ""

# NOTE: translated comment in English.
export ALIBABA_CLOUD_REGION="${ALIBABA_CLOUD_REGION:-ap-southeast-1}"
# NOTE: translated comment in English.
export ALIBABA_CLOUD_VSWITCH_ID="${ALIBABA_CLOUD_VSWITCH_ID:-}"
PUBLIC_IP=""
if command -v aliyun &>/dev/null; then
  echo "========== 使用阿里云 CLI 创建 ECS（Region=$ALIBABA_CLOUD_REGION）=========="
  cd "$CLAWJOB_ROOT"
  OUT=$(mktemp)
  if LOCAL_SSH_KEY_PATH="$KEY_PATH" bash deploy/create-ecs-singapore-cli.sh 2>&1 | tee "$OUT"; then
    PUBLIC_IP=$(grep -E "^PUBLIC_IP=" "$OUT" | cut -d= -f2)
  fi
  rm -f "$OUT"
fi

if [ -z "$PUBLIC_IP" ]; then
  echo "========== 使用 Python 脚本创建 ECS =========="
  [ -f "$PARENT/aliyun/accesskey.txt" ] && while IFS= read -r line; do
    [[ "$line" =~ ^accessKeyId[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_ID="${BASH_REMATCH[1]}"
    [[ "$line" =~ ^accessKeySecret[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_SECRET="${BASH_REMATCH[1]}"
  done < "$PARENT/aliyun/accesskey.txt"
  if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] || [ -z "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ]; then
    echo "错误：未配置阿里云 AccessKey。任选其一："
    echo "  1) 配置 CLI: aliyun configure"
    echo "  2) 环境变量: export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx ALIBABA_CLOUD_ACCESS_KEY_SECRET=yyy"
    echo "  3) 文件: 在 jasonproject/aliyun/accesskey.txt 写两行 accessKeyId xxx / accessKeySecret xxx"
    exit 1
  fi
  cd "$CLAWJOB_ROOT"
  pip install -q -r deploy/requirements-aliyun.txt 2>/dev/null || true
  OUT=$(mktemp)
  LOCAL_SSH_KEY_PATH="$KEY_PATH" ALIBABA_CLOUD_REGION=ap-southeast-1 ALIBABA_CLOUD_ECS_INSTANCE_TYPE=ecs.g6.large \
    python3 deploy/aliyun_ecs_create.py 2>&1 | tee "$OUT"
  PUBLIC_IP=$(grep -E "^PUBLIC_IP=" "$OUT" | cut -d= -f2)
  rm -f "$OUT"
fi

if [ -z "$PUBLIC_IP" ]; then
  echo "错误：未获取到公网 IP，请查看上方输出。"
  exit 1
fi

echo ""
echo "========== 写入 deploy/.deploy_env =========="
cat > "$SCRIPT_DIR/.deploy_env" << EOF
SERVER_IP=$PUBLIC_IP
DEPLOY_SSH_KEY=$KEY_PATH
EOF
export SERVER_IP="$PUBLIC_IP"
export DEPLOY_SSH_KEY="$KEY_PATH"
SSH_CMD="ssh -i $KEY_PATH -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"

echo "========== 等待 SSH 就绪 =========="
for i in $(seq 1 24); do
  if $SSH_CMD "root@$PUBLIC_IP" "echo ok" 2>/dev/null; then
    echo "SSH 已就绪"
    break
  fi
  echo "等待 SSH... ($i/24)"
  sleep 10
  [ "$i" -eq 24 ] && echo "SSH 超时" && exit 1
done

echo "========== ECS 安装 Docker / Nginx / 官网目录 =========="
$SSH_CMD "root@$PUBLIC_IP" "bash -s" << 'REMOTE'
set -e
command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)
mkdir -p /var/www/clawjob-website
command -v nginx >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq nginx)
cat > /etc/nginx/sites-available/default << 'NGX'
server {
    listen 80 default_server;
    root /var/www/clawjob-website;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
NGX
nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true
echo "OK"
REMOTE

echo "========== 部署官网 + ClawJob =========="
cd "$PARENT"
bash clawjob/deploy/deploy-all.sh

echo "========== 功能验证 =========="
cd "$CLAWJOB_ROOT"
export CLAWJOB_API_URL="http://$PUBLIC_IP:8000"
python3 deploy/verify-deployed.py "http://$PUBLIC_IP:8000" || true

echo ""
echo "========== 完成 =========="
echo "  官网:     http://$PUBLIC_IP/"
echo "  任务大厅: http://$PUBLIC_IP:3000"
echo "  后端 API: http://$PUBLIC_IP:8000"
echo "  SSH:      ssh -i $KEY_PATH root@$PUBLIC_IP"
echo "  日志:     $LOG"
