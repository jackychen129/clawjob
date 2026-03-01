#!/bin/bash
# 本地运行 API 测试 + 可选：验证线上 API
# 用法：
#   ./deploy/run-tests-and-verify.sh              # 仅本地 pytest
#   ./deploy/run-tests-and-verify.sh http://43.99.97.240:8000   # 本地测试 + 线上验证

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$(cd "$SCRIPT_DIR/../backend" && pwd)"

echo "========== 1. ClawJob 后端 API 测试（本地） =========="
cd "$BACKEND"
python -m pytest tests/test_clawjob_api.py -v --tb=short
echo ""

if [ -n "$1" ]; then
  echo "========== 2. 线上 API 验证: $1 =========="
  python3 "$SCRIPT_DIR/verify-deployed.py" "$1"
  echo ""
fi
echo "完成。"
