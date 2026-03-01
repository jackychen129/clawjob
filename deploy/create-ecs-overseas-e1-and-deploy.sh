#!/bin/bash
# 在多个海外地域依次尝试用 ecs.e-c1m2.large 创建 ECS，第一个成功的地域创建完后自动部署官网+ClawJob。
# 用法：cd /path/to/jasonproject && bash clawjob/deploy/create-ecs-overseas-e1-and-deploy.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
LOG="$SCRIPT_DIR/create-overseas-e1-deploy.log"
exec > >(tee -a "$LOG") 2>&1

KEY_PATH="${LOCAL_SSH_KEY_PATH:-$HOME/Downloads/newclawjobkey.pem}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"
INSTANCE_TYPE="ecs.e-c1m2.large"
# 海外地域顺序：香港、日本、悉尼、美国西/东、马来、印尼、德国、英国等
REGIONS="cn-hongkong ap-northeast-1 ap-southeast-2 us-west-1 us-east-1 ap-southeast-3 ap-southeast-5 ap-southeast-1 eu-central-1 eu-west-1"

echo "========== $(date '+%Y-%m-%d %H:%M:%S') 海外 ecs.e-c1m2.large 创建并部署 =========="
echo "规格: $INSTANCE_TYPE  密钥: $KEY_PATH"
echo ""

[ -f "$PARENT/aliyun/accesskey.txt" ] && while IFS= read -r line; do
  [[ "$line" =~ ^accessKeyId[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_ID="${BASH_REMATCH[1]}"
  [[ "$line" =~ ^accessKeySecret[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_SECRET="${BASH_REMATCH[1]}"
done < "$PARENT/aliyun/accesskey.txt"
if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] || [ -z "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ]; then
  echo "错误：请配置阿里云 AccessKey（环境变量或 jasonproject/aliyun/accesskey.txt）"
  exit 1
fi

cd "$CLAWJOB_ROOT"
pip install -q -r deploy/requirements-aliyun.txt 2>/dev/null || true

PUBLIC_IP=""
SUCCESS_REGION=""
for REGION in $REGIONS; do
  echo "========== 尝试地域: $REGION =========="
  OUT=$(mktemp)
  unset ALIBABA_CLOUD_VSWITCH_ID
  LOCAL_SSH_KEY_PATH="$KEY_PATH" ALIBABA_CLOUD_REGION="$REGION" \
    ALIBABA_CLOUD_ECS_INSTANCE_TYPE="$INSTANCE_TYPE" \
    ALIBABA_CLOUD_ECS_CHARGE_TYPE="${ALIBABA_CLOUD_ECS_CHARGE_TYPE:-PostPaid}" \
    python3 deploy/aliyun_ecs_create.py 2>&1 | tee "$OUT"
  PUBLIC_IP=$(grep -E "^PUBLIC_IP=" "$OUT" | cut -d= -f2)
  rm -f "$OUT"
  if [ -n "$PUBLIC_IP" ]; then
    SUCCESS_REGION="$REGION"
    echo "创建成功: 地域=$REGION 公网IP=$PUBLIC_IP"
    break
  fi
  echo "地域 $REGION 未成功，尝试下一地域..."
  echo ""
done

if [ -z "$PUBLIC_IP" ]; then
  echo "错误：所有海外地域均未成功创建 $INSTANCE_TYPE，请查看上方输出。"
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
echo "  地域:     $SUCCESS_REGION"
echo "  官网:     http://$PUBLIC_IP/"
echo "  任务大厅: http://$PUBLIC_IP:3000"
echo "  后端 API: http://$PUBLIC_IP:8000"
echo "  SSH:      ssh -i $KEY_PATH root@$PUBLIC_IP"
echo "  日志:     $LOG"
