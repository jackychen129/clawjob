#!/bin/bash
# 在服务器本机执行，用于诊断官网 / 任务大厅 / 后端是否正常。
# 用法：SSH 登录服务器后执行：
#   bash /opt/clawjob/deploy/verify-on-server.sh
# 或本机：ssh root@43.99.97.240 'bash -s' < deploy/verify-on-server.sh

echo "========== 1. Docker 容器状态 =========="
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "docker 未运行或无权执行"
echo ""

echo "========== 2. 本机端口连通性 =========="
for port in 80 3000 8000; do
  if command -v curl &>/dev/null; then
    if [ "$port" = "8000" ]; then
      code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://127.0.0.1:8000/health" 2>/dev/null || echo "000")
    else
      code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "http://127.0.0.1:${port}/" 2>/dev/null || echo "000")
    fi
    echo "  port ${port}: HTTP ${code}"
  else
    (echo >/dev/tcp/127.0.0.1/${port}) 2>/dev/null && echo "  port ${port}: open" || echo "  port ${port}: closed/fail"
  fi
done
echo ""

echo "========== 3. 后端 API 健康检查 =========="
curl -s -m 5 http://127.0.0.1:8000/health 2>/dev/null | head -c 400 || echo "  [FAIL] 无法访问 8000"
echo ""
echo ""

echo "========== 4. 任务大厅前端 (3000) =========="
curl -s -m 5 -o /dev/null -w "  HTTP %{http_code}\n" http://127.0.0.1:3000/ 2>/dev/null || echo "  [FAIL] 无法访问 3000"
echo ""

echo "========== 5. 官网 / Nginx (80) =========="
curl -s -m 5 -o /dev/null -w "  HTTP %{http_code}\n" http://127.0.0.1:80/ 2>/dev/null || echo "  [FAIL] 无法访问 80"
echo ""

echo "========== 6. 本机 API 全流程快速校验 =========="
if command -v python3 &>/dev/null && [ -d /opt/clawjob ]; then
  (cd /opt/clawjob && python3 deploy/verify-deployed.py http://127.0.0.1:8000 2>/dev/null) | tail -25 || echo "  (跳过：验证脚本失败)"
else
  echo "  (跳过：未安装 python3 或非 /opt/clawjob 部署)"
fi
echo ""
echo "完成。若本机 2/3/4/5 均正常而外网仍不可访问，请检查云厂商防火墙是否放行 80、3000、8000。"
