#!/bin/bash
# 通过阿里云 CLI 查找并重启 ECS 实例（按 INSTANCE_ID 或公网 IP）
#
# 环境变量 / deploy/.deploy_env:
#   ALIBABA_CLOUD_REGION           默认 ap-southeast-1
#   ALIBABA_CLOUD_ECS_INSTANCE_ID  可选；未设置则按 SERVER_IP 查找
#   SERVER_IP                      deploy/.deploy_env 中的公网 IP
#
# 用法:
#   ./deploy/aliyun-reboot-ecs.sh              # 重启
#   ./deploy/aliyun-reboot-ecs.sh --find-only  # 仅输出实例 ID（stdout 最后一行）

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi

REGION="${ALIBABA_CLOUD_REGION:-ap-southeast-1}"
INSTANCE_ID="${ALIBABA_CLOUD_ECS_INSTANCE_ID:-}"
SERVER_IP="${SERVER_IP:-}"
FIND_ONLY=0
for arg in "$@"; do
  [ "$arg" = "--find-only" ] && FIND_ONLY=1
done

if ! command -v aliyun >/dev/null 2>&1; then
  echo "错误：未安装 aliyun CLI。见 https://help.aliyun.com/document_detail/121541.html" >&2
  exit 1
fi

find_instance_by_ip() {
  local ip="$1" page=1
  while [ "$page" -le 20 ]; do
    local json
    json="$(aliyun ecs DescribeInstances --RegionId "$REGION" --PageSize 100 --PageNumber "$page" 2>&1)" || {
      echo "$json" >&2
      return 1
    }
    local found
    found="$(echo "$json" | python3 -c "
import json, sys
ip = sys.argv[1]
data = json.load(sys.stdin)
for inst in data.get('Instances', {}).get('Instance', []) or []:
    for addr in inst.get('PublicIpAddress', {}).get('IpAddress', []) or []:
        if addr == ip:
            print(inst.get('InstanceId', ''))
            sys.exit(0)
    eip = inst.get('EipAddress', {}).get('IpAddress')
    if eip == ip:
        print(inst.get('InstanceId', ''))
        sys.exit(0)
" "$ip" 2>/dev/null || true)"

    if [ -n "$found" ]; then
      echo "$found"
      return 0
    fi
    local total
    total="$(echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('TotalCount',0))" 2>/dev/null || echo 0)"
    if [ "$((page * 100))" -ge "$total" ]; then
      break
    fi
    page=$((page + 1))
  done
  return 1
}

if [ -z "$INSTANCE_ID" ]; then
  if [ -z "$SERVER_IP" ]; then
    echo "错误：请设置 ALIBABA_CLOUD_ECS_INSTANCE_ID 或 SERVER_IP" >&2
    exit 1
  fi
  echo "按公网 IP ${SERVER_IP} 在 ${REGION} 查找实例..." >&2
  INSTANCE_ID="$(find_instance_by_ip "$SERVER_IP" || true)"
  if [ -z "$INSTANCE_ID" ]; then
    echo "未找到实例。请确认地域 ${REGION} 或在 .deploy_env 填写 ALIBABA_CLOUD_ECS_INSTANCE_ID" >&2
    exit 1
  fi
fi

echo "$INSTANCE_ID"
[ "$FIND_ONLY" = 1 ] && exit 0

echo "重启实例 ${INSTANCE_ID}（${REGION}，ForceStop=true）..." >&2
aliyun ecs RebootInstance --RegionId "$REGION" --InstanceId "$INSTANCE_ID" --ForceStop true
echo "RebootInstance 已提交" >&2
