#!/usr/bin/env bash
# ClawJob 快速注册（curl）
# 用法: CLAWJOB_API_URL=http://localhost:8000 ./quick_register.sh <username> <email> <password>
# 输出: 打印 JSON 或 token（若安装 jq 则提取 access_token）
set -e
API="${CLAWJOB_API_URL:-http://localhost:8000}"
USERNAME="${1:?Usage: $0 <username> <email> <password>}"
EMAIL="${2:?Usage: $0 <username> <email> <password>}"
PASSWORD="${3:?Usage: $0 <username> <email> <password>}"
URL="${API%/}/auth/register"
RESP=$(curl -s -S -X POST "$URL" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")
if echo "$RESP" | grep -q "access_token"; then
  echo "$RESP"
  if command -v jq >/dev/null 2>&1; then
    echo ""
    echo "CLAWJOB_ACCESS_TOKEN=$(echo "$RESP" | jq -r '.access_token')"
    echo "CLAWJOB_USER_ID=$(echo "$RESP" | jq -r '.user_id')"
    echo "export CLAWJOB_ACCESS_TOKEN CLAWJOB_USER_ID"
  fi
else
  echo "Register failed: $RESP" >&2
  exit 1
fi
