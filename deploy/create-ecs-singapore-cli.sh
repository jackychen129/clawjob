#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
#
# NOTE: translated comment in English.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
REGION="${ALIBABA_CLOUD_REGION:-ap-southeast-1}"
export ALIBABA_CLOUD_REGION="$REGION"
INSTANCE_TYPE="${ALIBABA_CLOUD_ECS_INSTANCE_TYPE:-ecs.g6.large}"
KEY_PATH="${LOCAL_SSH_KEY_PATH:-$HOME/Downloads/newclawjobkey.pem}"
KEY_PATH="${KEY_PATH/#\~/$HOME}"

if ! command -v aliyun &>/dev/null; then
  echo "错误：未找到 aliyun CLI。请安装：https://help.aliyun.com/zh/cli/"
  exit 1
fi
if [ ! -f "$KEY_PATH" ]; then
  echo "错误：本机密钥不存在: $KEY_PATH"
  echo "请设置 LOCAL_SSH_KEY_PATH 或将密钥放到 ~/Downloads/newclawjobkey.pem"
  exit 1
fi

# NOTE: translated comment in English.
PUBLIC_KEY=$(ssh-keygen -y -f "$KEY_PATH" 2>/dev/null | tr -d '\n')
if [ -z "$PUBLIC_KEY" ]; then
  echo "错误：无法从 $KEY_PATH 导出公钥（需 ssh-keygen）"
  exit 1
fi

KEY_PAIR_NAME="clawjob-ecs-key-$(date +%s)"
echo "========== 1. 导入密钥对（$REGION）=========="
aliyun ecs ImportKeyPair --RegionId "$REGION" --KeyPairName "$KEY_PAIR_NAME" --PublicKeyBody "$PUBLIC_KEY"
echo ""

echo "========== 2. 获取 VPC / VSwitch =========="
VPC_JSON=$(aliyun vpc DescribeVpcs --RegionId "$REGION" 2>/dev/null || true)
VPC_ID=$(echo "$VPC_JSON" | grep -o '"VpcId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$VPC_ID" ]; then
  echo "未找到 VPC，尝试创建..."
  VPC_JSON=$(aliyun vpc CreateVpc --RegionId "$REGION" --CidrBlock 10.0.0.0/8 --VpcName clawjob-vpc 2>/dev/null)
  VPC_ID=$(echo "$VPC_JSON" | grep -o '"VpcId":"[^"]*"' | head -1 | cut -d'"' -f4)
  sleep 3
fi
[ -z "$VPC_ID" ] && echo "错误：无法获取 VpcId" && exit 1

VSW_JSON=$(aliyun vpc DescribeVSwitches --RegionId "$REGION" --VpcId "$VPC_ID" 2>/dev/null || true)
VSWITCH_ID=$(echo "$VSW_JSON" | grep -o '"VSwitchId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$VSWITCH_ID" ]; then
  VSW_JSON=$(aliyun vpc DescribeVSwitches --RegionId "$REGION" 2>/dev/null)
  VSWITCH_ID=$(echo "$VSW_JSON" | grep -o '"VSwitchId":"[^"]*"' | head -1 | cut -d'"' -f4)
fi
[ -z "$VSWITCH_ID" ] && echo "错误：该地域无可用交换机，请在控制台创建 VPC 与交换机后重试" && exit 1
echo "VpcId=$VPC_ID  VSwitchId=$VSWITCH_ID"
echo ""

echo "========== 3. 安全组（放行 22/80/443/3000/8000）=========="
SG_JSON=$(aliyun ecs DescribeSecurityGroups --RegionId "$REGION" --VpcId "$VPC_ID" 2>/dev/null || true)
SG_ID=$(echo "$SG_JSON" | grep -o '"SecurityGroupId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$SG_ID" ]; then
  SG_JSON=$(aliyun ecs CreateSecurityGroup --RegionId "$REGION" --VpcId "$VPC_ID" --SecurityGroupName clawjob-sg 2>/dev/null)
  SG_ID=$(echo "$SG_JSON" | grep -o '"SecurityGroupId":"[^"]*"' | head -1 | cut -d'"' -f4)
  sleep 2
  for port in 22 80 443 3000 8000; do
    aliyun ecs AuthorizeSecurityGroup \
      --RegionId "$REGION" \
      --SecurityGroupId "$SG_ID" \
      --IpProtocol tcp \
      --PortRange "$port/$port" \
      --SourceCidrIp 0.0.0.0/0 2>/dev/null || true
  done
  echo "已创建安全组并放行 22,80,443,3000,8000"
else
  for port in 22 80 443 3000 8000; do
    aliyun ecs AuthorizeSecurityGroup \
      --RegionId "$REGION" \
      --SecurityGroupId "$SG_ID" \
      --IpProtocol tcp \
      --PortRange "$port/$port" \
      --SourceCidrIp 0.0.0.0/0 2>/dev/null || true
  done
  echo "已放行 22,80,443,3000,8000"
fi
echo ""

echo "========== 4. 获取 Ubuntu 22 镜像 =========="
IMG_JSON=$(aliyun ecs DescribeImages \
  --RegionId "$REGION" \
  --ImageOwnerAlias system \
  --OSType linux \
  --Architecture x86_64 \
  --InstanceType "$INSTANCE_TYPE" \
  --PageSize 50 2>/dev/null)
IMAGE_ID=$(echo "$IMG_JSON" | grep -o '"ImageId":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$IMAGE_ID" ]; then
  IMG_JSON=$(aliyun ecs DescribeImages --RegionId "$REGION" --ImageOwnerAlias system --OSType linux --PageSize 20 2>/dev/null)
  IMAGE_ID=$(echo "$IMG_JSON" | grep -o '"ImageId":"[^"]*"' | head -1 | cut -d'"' -f4)
fi
[ -z "$IMAGE_ID" ] && echo "错误：未找到可用镜像" && exit 1
echo "ImageId=$IMAGE_ID"
echo ""

# NOTE: translated comment in English.
CHARGE_TYPE="${ALIBABA_CLOUD_ECS_CHARGE_TYPE:-PrePaid}"
PERIOD="${ALIBABA_CLOUD_ECS_PERIOD:-1}"
echo "========== 5. 创建实例（$INSTANCE_TYPE，$CHARGE_TYPE，${PERIOD}月）=========="
RUN_JSON=$(aliyun ecs RunInstances \
  --RegionId "$REGION" \
  --ImageId "$IMAGE_ID" \
  --InstanceType "$INSTANCE_TYPE" \
  --SecurityGroupId "$SG_ID" \
  --VSwitchId "$VSWITCH_ID" \
  --InstanceName clawjob-ecs \
  --HostName clawjob \
  --Amount 1 \
  --InstanceChargeType "$CHARGE_TYPE" \
  --Period "$PERIOD" \
  --PeriodUnit Month \
  --InternetChargeType PayByTraffic \
  --InternetMaxBandwidthOut 5 \
  --SystemDisk.Category cloud_essd \
  --SystemDisk.Size 100 \
  --KeyPairName "$KEY_PAIR_NAME" 2>&1)
# NOTE: translated comment in English.
INSTANCE_ID=$(echo "$RUN_JSON" | grep -oE '"InstanceId":"(i-[a-zA-Z0-9]+)"' | head -1 | cut -d'"' -f4)
[ -z "$INSTANCE_ID" ] && INSTANCE_ID=$(echo "$RUN_JSON" | grep -oE '"(i-[a-zA-Z0-9]{10,})"' | head -1 | tr -d '"')
if [ -z "$INSTANCE_ID" ]; then
  echo "$RUN_JSON"
  echo "创建失败（若报 InstanceType 不可用，可设置 ALIBABA_CLOUD_ECS_INSTANCE_TYPE=ecs.c6.large 重试）"
  exit 1
fi
echo "InstanceId=$INSTANCE_ID"
echo ""

echo "========== 6. 等待运行并获取公网 IP =========="
for i in $(seq 1 36); do
  sleep 10
  DESC=$(aliyun ecs DescribeInstances --RegionId "$REGION" --InstanceIds "[\"$INSTANCE_ID\"]" 2>/dev/null)
  STATUS=$(echo "$DESC" | grep -o '"Status":"[^"]*"' | head -1 | cut -d'"' -f4)
  PUBLIC_IP=$(echo "$DESC" | grep -oE '"PublicIpAddress"\s*:\s*\["[0-9.]+"\]' | grep -oE '[0-9.]+' | head -1)
  [ -z "$PUBLIC_IP" ] && PUBLIC_IP=$(echo "$DESC" | grep -oE '"IpAddress"\s*:\s*"[0-9.]+"' | head -1 | cut -d'"' -f4)
  [ -z "$PUBLIC_IP" ] && PUBLIC_IP=$(echo "$DESC" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | head -1)
  if [ "$STATUS" = "Running" ] && [ -n "$PUBLIC_IP" ]; then
    echo "INSTANCE_ID=$INSTANCE_ID"
    echo "PUBLIC_IP=$PUBLIC_IP"
    echo "REGION=$REGION"
    echo ""
    echo "SSH 登录: ssh -i $KEY_PATH root@$PUBLIC_IP"
    echo "部署: 将 deploy/.deploy_env 设为 SERVER_IP=$PUBLIC_IP、DEPLOY_SSH_KEY=$KEY_PATH 后执行 bash deploy/create-ecs-singapore-and-deploy.sh 的步骤 2 起，或直接 bash deploy/deploy-all.sh"
    exit 0
  fi
  echo "等待实例运行... ($i/36) Status=$STATUS"
done
echo "超时，请到控制台查看实例 $INSTANCE_ID"
echo "INSTANCE_ID=$INSTANCE_ID"
exit 1
