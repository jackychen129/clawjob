#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.

set -e

echo ">>> 安装 Docker（若未安装）..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sh
  apt-get install -y docker-compose-plugin || true
fi

echo ">>> 安装 Nginx（若未安装）..."
if ! command -v nginx &>/dev/null; then
  apt-get update && apt-get install -y nginx
fi

echo ">>> 创建官网站点目录..."
mkdir -p /var/www/clawjob-website

echo ">>> 配置 Nginx：80 指向官网..."
cat > /etc/nginx/sites-available/clawjob-website << 'NGINX'
server {
    listen 80 default_server;
    server_name _;
    root /var/www/clawjob-website;
    index index.html;

    location = /index.html {
        try_files $uri =404;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
    location / {
        try_files $uri $uri/ /index.html;
    }
    location /assets/ {
        add_header Cache-Control "public, max-age=31536000, immutable";
    }
    location ~* \.(js|css|ico|svg|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/clawjob-website /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo ">>> 放行防火墙端口 80, 3000, 8000（若使用 ufw）..."
if command -v ufw &>/dev/null; then
  ufw allow 80/tcp 2>/dev/null || true
  ufw allow 3000/tcp 2>/dev/null || true
  ufw allow 8000/tcp 2>/dev/null || true
  ufw --force enable 2>/dev/null || true
fi

echo ">>> 若在阿里云轻量控制台，请确认防火墙规则已放行：80, 3000, 8000 (TCP)"
echo ">>> 完成。请从本机执行一键部署脚本上传代码并启动 Docker。"
