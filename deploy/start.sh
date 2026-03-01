#!/bin/bash
# Agent Arena - Docker 全栈一键启动
set -e
cd "$(dirname "$0")"
echo "正在启动 Agent Arena 全栈..."
docker compose -f docker-compose.yml up -d --build
echo ""
echo "启动完成。等待服务就绪（约 30–60 秒）..."
sleep 5
docker compose -f docker-compose.yml ps
echo ""
echo "访问地址："
echo "  前端:    http://localhost:3000"
echo "  后端 API: http://localhost:8000"
echo "  API 文档: http://localhost:8000/docs"
echo ""
echo "查看日志: docker compose -f docker-compose.yml logs -f"
echo "停止服务: docker compose -f docker-compose.yml down"
