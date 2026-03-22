#!/bin/bash
# 本地运行 API 测试 + 前端单元测试 + 可选：验证线上 API
# 用法：
#   ./deploy/run-tests-and-verify.sh              # pytest + frontend vitest + build
#   ./deploy/run-tests-and-verify.sh http://43.99.97.240:8000   # 上述 + 线上 verify-deployed

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "========== 1. ClawJob 后端 API 测试（本地） =========="
cd "$BACKEND"
python -m pytest tests/test_clawjob_api.py -v --tb=short
echo ""

echo "========== 2. 前端单元测试（Vitest） =========="
cd "$FRONTEND"
npm run test:run
echo ""

echo "========== 3. 前端构建检查 =========="
npm run build
echo ""

if [ -n "$1" ]; then
  echo "========== 4. 线上 API 验证: $1 =========="
  python3 "$SCRIPT_DIR/verify-deployed.py" "$1"
  echo ""
fi
echo "完成。"
