#!/bin/bash
# 一键：在新加坡创建 ECS（ecs.e-c1m2.large、使用本机密钥）、部署官网+ClawJob、并验证。
# 前置：阿里云 AccessKey、本机密钥 ~/Downloads/newclawjobkey.pem（或设置 LOCAL_SSH_KEY_PATH）
# 用法：在 jasonproject 下执行（与 clawjob、clawjob-website 同级）：
#   cd /path/to/jasonproject && bash clawjob/deploy/create-ecs-singapore-and-deploy.sh
#
# 或先配置密钥：export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx ALIBABA_CLOUD_ACCESS_KEY_SECRET=yyy

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
# 从 aliyun/accesskey.txt 读取（若存在）
if [ -f "$PARENT/aliyun/accesskey.txt" ]; then
  while IFS= read -r line; do
    [[ "$line" =~ ^accessKeyId[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_ID="${BASH_REMATCH[1]}"
    [[ "$line" =~ ^accessKeySecret[[:space:]]+(.+)$ ]] && export ALIBABA_CLOUD_ACCESS_KEY_SECRET="${BASH_REMATCH[1]}"
  done < "$PARENT/aliyun/accesskey.txt"
fi

KEY_PATH="${LOCAL_SSH_KEY_PATH:-$HOME/Downloads/newclawjobkey.pem}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"
if [ ! -f "$KEY_PATH" ]; then
  echo "错误：本机密钥不存在: $KEY_PATH"
  echo "请设置 LOCAL_SSH_KEY_PATH 或将密钥放到 ~/Downloads/newclawjobkey.pem"
  exit 1
fi

if [ -z "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] || [ -z "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ]; then
  echo "错误：请设置阿里云 AccessKey："
  echo "  export ALIBABA_CLOUD_ACCESS_KEY_ID=xxx"
  echo "  export ALIBABA_CLOUD_ACCESS_KEY_SECRET=yyy"
  echo "或在 $PARENT/aliyun/accesskey.txt 中配置两行 accessKeyId / accessKeySecret"
  exit 1
fi

echo "========== 1. 创建新加坡 ECS（ecs.e-c1m2.large，绑定你的密钥）=========="
cd "$CLAWJOB_ROOT"
pip install -q -r deploy/requirements-aliyun.txt 2>/dev/null || true
OUTPUT=$(mktemp)
LOCAL_SSH_KEY_PATH="$KEY_PATH" ALIBABA_CLOUD_REGION=ap-southeast-1 ALIBABA_CLOUD_ECS_INSTANCE_TYPE=ecs.e-c1m2.large \
  python3 deploy/aliyun_ecs_create.py 2>&1 | tee "$OUTPUT"
PUBLIC_IP=$(grep -E "^PUBLIC_IP=" "$OUTPUT" | cut -d= -f2)
INSTANCE_ID=$(grep -E "^INSTANCE_ID=" "$OUTPUT" | cut -d= -f2)
rm -f "$OUTPUT"
if [ -z "$PUBLIC_IP" ]; then
  echo "创建 ECS 未返回公网 IP，请查看上方输出。若实例已创建，可手动设置 SERVER_IP 后执行 deploy-all.sh"
  exit 1
fi
echo "已创建实例 $INSTANCE_ID，公网 IP: $PUBLIC_IP"
echo ""

echo "========== 2. 写入 deploy/.deploy_env 并等待 SSH 可用 =========="
mkdir -p "$SCRIPT_DIR"
cat > "$SCRIPT_DIR/.deploy_env" << EOF
SERVER_IP=$PUBLIC_IP
DEPLOY_SSH_KEY=$KEY_PATH
EOF
export SERVER_IP="$PUBLIC_IP"
export DEPLOY_SSH_KEY="$KEY_PATH"
SSH_CMD="ssh -i $KEY_PATH -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10"
for i in 1 2 3 4 5 6 7 8 9 10 11 12; do
  if $SSH_CMD "root@$PUBLIC_IP" "echo ok" 2>/dev/null; then
    echo "SSH 已就绪"
    break
  fi
  echo "等待 SSH... ($i/12)"
  sleep 15
  if [ "$i" -eq 12 ]; then
    echo "SSH 超时，请稍后在控制台确认实例已运行，再执行: SERVER_IP=$PUBLIC_IP bash clawjob/deploy/deploy-all.sh"
    exit 1
  fi
done
echo ""

echo "========== 3. 在 ECS 上安装 Docker、Nginx 与官网目录 =========="
$SSH_CMD "root@$PUBLIC_IP" "bash -s" << 'REMOTE'
set -e
command -v docker >/dev/null 2>&1 || (curl -fsSL https://get.docker.com | sh)
mkdir -p /var/www/clawjob-website
command -v nginx >/dev/null 2>&1 || (apt-get update -qq && apt-get install -y -qq nginx)
# 简单 Nginx 默认站：80 指向 /var/www/clawjob-website
cat > /etc/nginx/sites-available/default << 'NGX'
server {
    listen 80 default_server;
    root /var/www/clawjob-website;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
NGX
nginx -t 2>/dev/null && systemctl reload nginx 2>/dev/null || true
echo "Docker and Nginx ready"
REMOTE
echo ""

echo "========== 4. 部署官网 + ClawJob（任务大厅+后端）=========="
cd "$PARENT"
export SERVER_IP
export DEPLOY_SSH_KEY
bash clawjob/deploy/deploy-all.sh
echo ""

echo "========== 5. 功能验证 =========="
cd "$CLAWJOB_ROOT"
export CLAWJOB_API_URL="http://$PUBLIC_IP:8000"
python3 deploy/verify-deployed.py "http://$PUBLIC_IP:8000" || true
echo ""
echo "========== 完成 =========="
echo "  官网:     http://$PUBLIC_IP/"
echo "  任务大厅: http://$PUBLIC_IP:3000"
echo "  后端 API: http://$PUBLIC_IP:8000"
echo "  SSH:      ssh -i $KEY_PATH root@$PUBLIC_IP"
