#!/bin/bash
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
#
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.
# NOTE: translated comment in English.

set -e
DOMAIN="${DOMAIN:-}"
if [ -z "$DOMAIN" ]; then
  echo "请设置 DOMAIN，例如：DOMAIN=clawjob.com $0"
  exit 1
fi

# NOTE: translated comment in English.
CERTBOT_EMAIL="${CERTBOT_EMAIL:-}"

echo "========== Let's Encrypt SSL 配置 =========="
echo "域名: $DOMAIN"
echo "将申请: $DOMAIN, www.$DOMAIN, app.$DOMAIN, api.$DOMAIN"
echo ""

# NOTE: translated comment in English.
if ! command -v nginx &>/dev/null; then
  echo ">>> 安装 Nginx ..."
  apt-get update -qq
  apt-get install -y -qq nginx
  systemctl enable nginx
  systemctl start nginx
fi

# NOTE: translated comment in English.
if ! command -v certbot &>/dev/null; then
  echo ">>> 安装 certbot ..."
  apt-get update -qq
  apt-get install -y -qq certbot python3-certbot-nginx
fi

# NOTE: translated comment in English.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-.}")" && pwd)"
CLAWJOB_DEPLOY="$(cd "$SCRIPT_DIR/../.." 2>/dev/null && pwd)"
NGINX_CONF_SRC="$CLAWJOB_DEPLOY/deploy/nginx/clawjob-ssl.conf"
if [ ! -f "$NGINX_CONF_SRC" ]; then
  NGINX_CONF_SRC="/opt/clawjob/deploy/nginx/clawjob-ssl.conf"
fi
if [ ! -f "$NGINX_CONF_SRC" ]; then
  echo "错误：未找到 nginx 模板 $NGINX_CONF_SRC"
  exit 1
fi

# NOTE: translated comment in English.
mkdir -p /var/www/clawjob-website
CONF_DEST="/etc/nginx/conf.d/clawjob.conf"
if [ -d /etc/nginx/sites-available ]; then
  CONF_DEST="/etc/nginx/sites-available/clawjob"
fi

sed "s/{{DOMAIN}}/$DOMAIN/g" "$NGINX_CONF_SRC" > "$CONF_DEST"
if [ -d /etc/nginx/sites-available ] && [ "$CONF_DEST" = "/etc/nginx/sites-available/clawjob" ]; then
  ln -sf /etc/nginx/sites-available/clawjob /etc/nginx/sites-enabled/clawjob 2>/dev/null || true
fi
# NOTE: translated comment in English.
rm -f /etc/nginx/sites-enabled/default /etc/nginx/sites-enabled/default.bak 2>/dev/null
echo ">>> 已移除 default 站点（若存在）"

echo ">>> Nginx 配置已写入 $CONF_DEST"
nginx -t
systemctl reload nginx
echo ">>> Nginx 已重载"

# NOTE: translated comment in English.
CERTBOT_OPTS=(--nginx -d "$DOMAIN" -d "www.$DOMAIN" -d "app.$DOMAIN" -d "api.$DOMAIN" --non-interactive --agree-tos)
if [ -n "$CERTBOT_EMAIL" ]; then
  CERTBOT_OPTS+=(--email "$CERTBOT_EMAIL")
else
  CERTBOT_OPTS+=(--register-unsafely-without-email)
fi

echo ">>> 申请 Let's Encrypt 证书（约 1 分钟）..."
certbot "${CERTBOT_OPTS[@]}"

# NOTE: translated comment in English.
if [ -d /etc/cron.d ]; then
  echo "SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin
0 3 1 * * root certbot renew --quiet --deploy-hook 'systemctl reload nginx'" > /etc/cron.d/certbot-clawjob
  chmod 644 /etc/cron.d/certbot-clawjob
  echo ">>> 已添加证书自动续期到 /etc/cron.d/certbot-clawjob（每月 1 日 03:00）"
fi

echo ""
echo "========== SSL 配置完成 =========="
echo "  https://$DOMAIN          → 官网"
echo "  https://www.$DOMAIN      → 官网"
echo "  https://app.$DOMAIN      → 任务大厅"
echo "  https://api.$DOMAIN      → 后端 API"
echo ""
echo "下一步："
echo "  1. 在 deploy/.env 中改为 https 与上述域名："
echo "     VITE_API_BASE_URL=https://api.$DOMAIN"
echo "     FRONTEND_URL=https://app.$DOMAIN"
echo "     CORS_ORIGINS=https://app.$DOMAIN"
echo "     GOOGLE_REDIRECT_URI=https://api.$DOMAIN/auth/google/callback  # 若用 Google 登录"
echo "  2. 重新构建并部署前端（使 VITE_API_BASE_URL 生效）"
echo "  3. 官网「体验任务大厅」链接改为 https://app.$DOMAIN（重新部署 clawjob-website 并设置 VITE_TASK_HALL_URL）"
echo "  4. 证书约 90 天有效；续期： certbot renew（可加 crontab 每月执行）"
echo ""
