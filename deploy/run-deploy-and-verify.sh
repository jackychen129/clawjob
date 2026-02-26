#!/bin/bash
# 本机一键：先部署，再验证并自动修复直到通过。
# 在能 SSH 到 43.99.97.240 的本机执行：./deploy/run-deploy-and-verify.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

echo "========== 第一步：部署（官网 + ClawJob + 数据库初始化） =========="
"$SCRIPT_DIR/deploy-all.sh"

echo ""
echo "========== 第二步：验证并自动修复直到通过 =========="
"$SCRIPT_DIR/verify-and-fix-until-pass.sh"

echo ""
echo "========== 全部完成 =========="
