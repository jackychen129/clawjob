#!/bin/bash
# 从项目根目录的 aliyun/accesskey.txt 读取密钥并创建新加坡 ECS。
# 用法：在 clawjob 目录执行 ./deploy/run_ecs_create_with_key.sh
# 或从 jasonproject 目录：clawjob/deploy/run_ecs_create_with_key.sh
# 请勿将 accesskey.txt 提交到 git。

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# 假设 clawjob 在 jasonproject 下，aliyun 与 clawjob 同级
PARENT="$(cd "$CLAWJOB_ROOT/.." && pwd)"
KEY_FILE="$PARENT/aliyun/accesskey.txt"

if [ ! -f "$KEY_FILE" ]; then
  echo "未找到 $KEY_FILE，请将 accessKeyId 与 accessKeySecret 按行写入该文件。" >&2
  exit 1
fi

export ALIBABA_CLOUD_ACCESS_KEY_ID=$(grep -E '^accessKeyId\s' "$KEY_FILE" | awk '{print $2}')
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=$(grep -E '^accessKeySecret\s' "$KEY_FILE" | awk '{print $2}')
[ -n "$ALIBABA_CLOUD_ACCESS_KEY_ID" ] || { echo "未从 $KEY_FILE 解析到 accessKeyId" >&2; exit 1; }
[ -n "$ALIBABA_CLOUD_ACCESS_KEY_SECRET" ] || { echo "未从 $KEY_FILE 解析到 accessKeySecret" >&2; exit 1; }

echo "已从 $KEY_FILE 加载密钥，地域默认新加坡 (ap-southeast-1) ..." >&2
cd "$CLAWJOB_ROOT"
python3 deploy/aliyun_ecs_create.py
