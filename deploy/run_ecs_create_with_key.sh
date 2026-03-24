#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
# NOTE: translated comment in English.
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
