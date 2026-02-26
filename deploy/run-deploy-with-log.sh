#!/bin/bash
# 包装 deploy-all.sh，把输出写入 deploy-last.log 便于查看
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/deploy-last.log"
exec > >(tee -a "$LOG") 2>&1
echo "=== $(date -Iseconds) 开始部署 ==="
cd "$SCRIPT_DIR/.."
"$SCRIPT_DIR/deploy-all.sh"
echo "=== 退出码 $? $(date -Iseconds) ==="
