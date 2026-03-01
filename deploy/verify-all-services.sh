#!/bin/bash
# 验证已部署的三大服务：官网(80)、任务大厅(3000)、后端 API(8000)。需在 jasonproject 下执行。
# 用法：bash clawjob/deploy/verify-all-services.sh [SERVER_IP]
# 未传 IP 时从 clawjob/deploy/.deploy_env 读取 SERVER_IP。

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAWJOB_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
SERVER_IP="${1:-$SERVER_IP}"
if [ -z "$SERVER_IP" ]; then
  echo "用法: bash clawjob/deploy/verify-all-services.sh [SERVER_IP]"
  echo "或在 deploy/.deploy_env 中设置 SERVER_IP"
  exit 1
fi

RESULT_FILE="$SCRIPT_DIR/verify-all-result.txt"
echo "验证时间: $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$RESULT_FILE"
echo "目标: $SERVER_IP" >> "$RESULT_FILE"
echo "" >> "$RESULT_FILE"

ok_80=0
ok_3000=0
ok_8000=0

echo "========== 1. 官网 (http://${SERVER_IP}/) =========="
if curl -sf --connect-timeout 8 "http://${SERVER_IP}/" -o /dev/null 2>/dev/null; then
  echo "[OK] 官网 80 可访问"
  echo "  官网(80): OK" >> "$RESULT_FILE"
  ok_80=1
else
  echo "[FAIL] 官网 80 无法访问"
  echo "  官网(80): FAIL" >> "$RESULT_FILE"
fi
echo ""

echo "========== 2. 任务大厅 (http://${SERVER_IP}:3000/) =========="
if curl -sf --connect-timeout 8 "http://${SERVER_IP}:3000/" -o /dev/null 2>/dev/null; then
  echo "[OK] 任务大厅 3000 可访问"
  echo "  任务大厅(3000): OK" >> "$RESULT_FILE"
  ok_3000=1
else
  echo "[FAIL] 任务大厅 3000 无法访问"
  echo "  任务大厅(3000): FAIL" >> "$RESULT_FILE"
fi
echo ""

echo "========== 3. 后端 API (http://${SERVER_IP}:8000/health) =========="
if curl -sf --connect-timeout 8 "http://${SERVER_IP}:8000/health" -o /dev/null 2>/dev/null; then
  echo "[OK] 后端 8000 健康检查可访问"
  echo "  后端(8000): OK" >> "$RESULT_FILE"
  ok_8000=1
else
  echo "[FAIL] 后端 8000 无法访问"
  echo "  后端(8000): FAIL" >> "$RESULT_FILE"
fi
echo ""

echo "========== 4. 后端 API 全流程校验 =========="
export CLAWJOB_API_URL="http://${SERVER_IP}:8000"
python3 "$SCRIPT_DIR/verify-deployed.py" "http://${SERVER_IP}:8000" 2>&1 | tee -a "$RESULT_FILE" || true
if [ -f "$SCRIPT_DIR/verify-result.txt" ] && grep -q "All checks passed" "$SCRIPT_DIR/verify-result.txt" 2>/dev/null; then
  echo "[OK] 后端 API 全流程通过"
else
  echo "[部分失败] 见上方输出与 deploy/verify-result.txt"
fi
echo "" >> "$RESULT_FILE"

echo "========== 汇总 =========="
echo "  官网:       $([ $ok_80 -eq 1 ] && echo '正常' || echo '不可用')  http://${SERVER_IP}/"
echo "  任务大厅:   $([ $ok_3000 -eq 1 ] && echo '正常' || echo '不可用')  http://${SERVER_IP}:3000"
echo "  后端 API:   $([ $ok_8000 -eq 1 ] && echo '正常' || echo '不可用')  http://${SERVER_IP}:8000"
echo ""
echo "结果已写入: $RESULT_FILE"

if [ $ok_80 -eq 1 ] && [ $ok_3000 -eq 1 ] && [ $ok_8000 -eq 1 ]; then
  echo "所有服务正常运行。"
  exit 0
else
  echo "部分服务不可用，请检查防火墙(80/3000/8000)与服务器上 docker ps。"
  exit 1
fi
