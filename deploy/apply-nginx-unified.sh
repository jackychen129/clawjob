#!/bin/bash
# 根域 / app / api 统一反代 Docker（合并 SPA）；修复重复 upstream 与静态官网配置
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
export SERVER_IP="${SERVER_IP:-8.216.64.80}"
export SITE_DOMAIN="${SITE_DOMAIN:-clawjob.com.cn}"
SSH_USER="${SSH_USER:-root}"

if [ -n "$DEPLOY_SSH_KEY" ]; then
  DEPLOY_SSH_KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
  SSH_CMD=(ssh -i "$DEPLOY_SSH_KEY" -o StrictHostKeyChecking=accept-new)
elif [ -n "$DEPLOY_SSH_PASSWORD" ] && command -v sshpass &>/dev/null; then
  export SSHPASS="$DEPLOY_SSH_PASSWORD"
  SSH_CMD=(sshpass -e ssh -o StrictHostKeyChecking=accept-new)
else
  SSH_CMD=(ssh -o StrictHostKeyChecking=accept-new)
fi

DOMAIN="$SITE_DOMAIN"
echo ">>> 应用统一 Nginx（$DOMAIN @ $SSH_USER@$SERVER_IP）"

"${SSH_CMD[@]}" "${SSH_USER}@${SERVER_IP}" "DOMAIN='$DOMAIN' bash -s" <<'REMOTE'
set -e
export DOMAIN="${DOMAIN:-clawjob.com.cn}"

# 若上次 patch 失败，从 .bak.unified 恢复
for f in /etc/nginx/sites-available/clawjob /etc/nginx/sites-enabled/clawjob; do
  if [ -f "${f}.bak.unified" ]; then
    cp "${f}.bak.unified" "$f"
  fi
done

# 移除可能失败的重复 unified 配置
rm -f /etc/nginx/sites-enabled/clawjob-unified /etc/nginx/sites-available/clawjob-unified 2>/dev/null || true
rm -f /etc/nginx/conf.d/clawjob-unified.conf 2>/dev/null || true

UP="/etc/nginx/conf.d/clawjob-upstream.conf"
if ! grep -rq 'upstream clawjob_backend' /etc/nginx/conf.d /etc/nginx/sites-enabled /etc/nginx/sites-available 2>/dev/null; then
  cat > "$UP" <<'UPSTREAM'
upstream clawjob_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}
upstream clawjob_frontend {
    server 127.0.0.1:3000;
    keepalive 16;
}
UPSTREAM
  echo "created $UP"
fi

python3 << 'PY'
import os
import pathlib
import re

domain = os.environ.get("DOMAIN", "clawjob.com.cn")
proxy_location = r"""
    location / {
        proxy_pass http://clawjob_frontend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }"""

api_location = r"""
    location / {
        proxy_pass http://clawjob_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }"""

roots = [
    pathlib.Path("/etc/nginx/sites-enabled"),
    pathlib.Path("/etc/nginx/conf.d"),
]
# 主配置（若未 symlink）
extra = pathlib.Path("/etc/nginx/sites-available/clawjob")
seen = set()
patched = []

candidates = list(roots)
if extra.is_file():
    candidates.append(extra)

for base in candidates:
    if base.is_file():
        paths = [base]
    elif base.is_dir():
        paths = [p for p in base.iterdir() if p.is_file() and ".bak" not in p.name]
    else:
        continue
    for p in sorted(paths):
        if p in seen:
            continue
        seen.add(p)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if domain not in text and "clawjob" not in text.lower():
            continue
        new = text
        # 静态官网 → 反代 SPA
        new = re.sub(
            r"root /var/www/clawjob-website;\s*\n\s*index index\.html;\s*\n\s*location / \{\s*\n\s*try_files[^}]+\}\s*",
            proxy_location + "\n",
            new,
            count=0,
        )
        new = re.sub(r"location = /index\.html \{[^}]+\}\s*", "", new, count=0)
        # api 子域若误指静态站
        if f"api.{domain}" in new and "clawjob-website" in new:
            new = re.sub(
                r"server_name api\." + re.escape(domain) + r"[^;]*;[\s\S]*?location / \{[^}]+\}",
                f"server_name api.{domain};\n" + api_location,
                new,
                count=1,
            )
        if new != text:
            bak = p.with_suffix(p.suffix + ".bak.unified")
            if not bak.exists():
                bak.write_text(text, encoding="utf-8")
            p.write_text(new, encoding="utf-8")
            patched.append(str(p))

for line in patched:
    print("patched", line)
if not patched:
    print("no patch needed (already proxying frontend)")
PY

# 禁用纯静态官网 default 站点
rm -f /etc/nginx/sites-enabled/clawjob-website 2>/dev/null || true

nginx -t
systemctl reload nginx
echo "Nginx reload OK"
REMOTE

echo ">>> 完成"
