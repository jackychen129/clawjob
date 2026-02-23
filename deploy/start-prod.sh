#!/bin/bash
# ClawJob 生产环境一键启动（Docker Compose）
# 使用前：在 deploy 目录下 cp .env.example .env 并修改配置
set -e
cd "$(dirname "$0")"

if [ ! -f .env ]; then
  echo "请先复制 .env.example 为 .env 并修改配置："
  echo "  cp .env.example .env && chmod 600 .env"
  exit 1
fi

echo "正在启动 ClawJob 生产栈..."
docker compose -f docker-compose.prod.yml --env-file .env up -d --build

echo ""
echo "等待后端就绪（约 30–60 秒）..."
sleep 15
docker compose -f docker-compose.prod.yml ps

echo ""
echo "首次部署或升级后，请执行数据库迁移："
echo "  docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 scripts/run_migrations.py'"
echo ""
echo "访问："
echo "  前端: http://<服务器IP>:3000"
echo "  后端: http://<服务器IP>:8000"
echo "  文档: http://<服务器IP>:8000/docs"
echo ""
echo "查看日志: docker compose -f docker-compose.prod.yml logs -f"
echo "停止: docker compose -f docker-compose.prod.yml down"
