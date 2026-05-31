# 根域与 app 共用同一前端（保留 HTTPS）

**当前线上**：根域与 www 已恢复为静态官网（clawjob-website），仅 **https://app.clawjob.com.cn** 为任务大厅。若要让根域与 app 共用同一前端，按下文操作。

让 **https://clawjob.com.cn**、**https://www.clawjob.com.cn** 与 **https://app.clawjob.com.cn** 使用同一套任务大厅前端，数据一致。  
只改根域对应的 server 块，**不动** api/app 的 443 配置和 Certbot 的 80 跳转，HTTPS 与证书保持不变。

---

## 一、在服务器上要改的内容

当前根域（clawjob.com.cn / www）的 **443 server 块** 是静态站：

```nginx
# 官网：https://clawjob.com.cn 与 https://www.clawjob.com.cn
server {
    server_name clawjob.com.cn www.clawjob.com.cn;
    root /var/www/clawjob-website;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/clawjob.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/clawjob.com.cn/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
```

把上面整块（从 `# 官网` 到闭合的 `}`）**替换成**下面这块（根域改为反代到前端，SSL 不变）：

```nginx
# 根域与 www：与 app 共用同一前端（任务大厅 SPA），数据与 app 一致
# 若需恢复静态官网，改回 root /var/www/clawjob-website; try_files $uri $uri/ /index.html;
server {
    server_name clawjob.com.cn www.clawjob.com.cn;
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
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/clawjob.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/clawjob.com.cn/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
```

其余配置（api、app、80 跳转、default_server 等）都**不要动**。

---

## 二、操作步骤（在服务器上执行）

### 1. 备份当前配置

```bash
sudo cp /etc/nginx/sites-available/clawjob.bak.20260310111106 /etc/nginx/sites-available/clawjob.bak.$(date +%Y%m%d%H%M%S)
```

### 2. 编辑配置

当前生效的是符号链接，实际文件在 `sites-available`：

```bash
sudo nano /etc/nginx/sites-available/clawjob.bak.20260310111106
```

找到以 `# 官网：https://clawjob.com.cn` 开头、到下一个 `server {` 之前的那一整块（包含 `root /var/www/clawjob-website` 和 `listen 443 ssl`），整块删除，粘贴为上面「替换成」里的那一整块，保存退出。

若你用的是 `vim`：

```bash
sudo vim /etc/nginx/sites-available/clawjob.bak.20260310111106
```

找到该 server 块，整块替换为上面的新块即可。

### 3. 检查并重载 Nginx

```bash
sudo nginx -t && sudo systemctl reload nginx
```

无报错即生效。再访问 https://clawjob.com.cn 应得到与 https://app.clawjob.com.cn 相同的任务大厅，且 HTTPS 正常。

---

## 三、用 sed 一键替换（可选）

若你希望用命令一次性替换，可在服务器上执行下面整段（会先备份再改）：

```bash
BACKUP="/etc/nginx/sites-available/clawjob.bak.$(date +%Y%m%d%H%M%S)"
sudo cp /etc/nginx/sites-available/clawjob.bak.20260310111106 "$BACKUP"

# 替换「官网」根域 443 块：从静态站改为反代到前端（保留 SSL）
sudo sed -i '/# 官网：https:\/\/clawjob.com.cn 与 https:\/\/www.clawjob.com.cn/,/^}$/{
  /# 官网：https:\/\/clawjob.com.cn 与 https:\/\/www.clawjob.com.cn/{
    r /dev/stdin
    d
  }
  /root \/var\/www\/clawjob-website;/d
  /try_files \$uri \$uri\/ \/index.html;/d
  /index index.html;/d
}' /etc/nginx/sites-available/clawjob.bak.20260310111106 << 'NGINX_BLOCK'

# 根域与 www：与 app 共用同一前端（任务大厅 SPA），数据与 app 一致
server {
    server_name clawjob.com.cn www.clawjob.com.cn;
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
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/clawjob.com.cn/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/clawjob.com.cn/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
NGINX_BLOCK

sudo nginx -t && sudo systemctl reload nginx
```

**注意**：sed 在不同系统上对多行匹配可能表现不一。若执行后 `nginx -t` 报错，请用第二节的手动编辑方式恢复备份并重新改。

### 方法 B：用 Python 一键替换（更稳妥）

在服务器上执行（会先备份再替换根域 443 块）：

```bash
CONF="/etc/nginx/sites-available/clawjob.bak.20260310111106"
sudo cp "$CONF" "${CONF}.bak.$(date +%Y%m%d%H%M%S)"
sudo python3 << 'PY'
path = "/etc/nginx/sites-available/clawjob.bak.20260310111106"
with open(path) as f:
    c = f.read()
old = "# 官网：https://clawjob.com.cn 与 https://www.clawjob.com.cn\nserver {\n    server_name clawjob.com.cn www.clawjob.com.cn;\n    root /var/www/clawjob-website;\n    index index.html;\n    location / {\n        try_files $uri $uri/ /index.html;\n    }\n\n    listen 443 ssl; # managed by Certbot\n    ssl_certificate /etc/letsencrypt/live/clawjob.com.cn/fullchain.pem; # managed by Certbot\n    ssl_certificate_key /etc/letsencrypt/live/clawjob.com.cn/privkey.pem; # managed by Certbot\n    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot\n    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot\n\n\n}\n"
new = "# 根域与 www：与 app 共用同一前端（任务大厅 SPA）\nserver {\n    server_name clawjob.com.cn www.clawjob.com.cn;\n    location / {\n        proxy_pass http://clawjob_frontend;\n        proxy_http_version 1.1;\n        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n        proxy_set_header X-Forwarded-Proto $scheme;\n        proxy_connect_timeout 60s;\n        proxy_send_timeout 60s;\n        proxy_read_timeout 60s;\n    }\n\n    listen 443 ssl; # managed by Certbot\n    ssl_certificate /etc/letsencrypt/live/clawjob.com.cn/fullchain.pem;\n    ssl_certificate_key /etc/letsencrypt/live/clawjob.com.cn/privkey.pem;\n    include /etc/letsencrypt/options-ssl-nginx.conf;\n    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;\n}\n"
if old not in c:
    raise SystemExit("未找到要替换的块，请用手动编辑（第二节）")
with open(path, "w") as f:
    f.write(c.replace(old, new, 1))
print("OK")
PY
sudo nginx -t && sudo systemctl reload nginx && echo "Done"
```

若报错「未找到要替换的块」，多半是备份里该 server 块空行或格式略有不同，请用手动编辑（第二节）。恢复备份：`sudo cp ${CONF}.bak.* $CONF` 后 `sudo systemctl reload nginx`。

---

## 四、恢复为静态官网（可选）

若之后希望根域再指向静态站，把该 443 server 块中的 `location /` 改回：

```nginx
    root /var/www/clawjob-website;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
```

并删掉该 server 块里的 `proxy_pass`、`proxy_*` 等行，保存后 `sudo nginx -t && sudo systemctl reload nginx` 即可。

---

## 五、简要检查

- **https://api.clawjob.com.cn/health** — 应返回 200
- **https://app.clawjob.com.cn/** — 任务大厅
- **https://clawjob.com.cn/** — 修改后应与 app 一致（同一前端、同一数据）
