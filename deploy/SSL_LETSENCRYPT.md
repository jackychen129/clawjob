# 使用 Let's Encrypt 免费 SSL 配置 HTTPS

本文说明在已部署 ClawJob 的服务器上，用 **Let's Encrypt** 免费证书开启 HTTPS，并让 Nginx 反代 80/443 到官网、任务大厅与后端 API。

---

## 零、本机一键自动化（推荐）

若已配置 `deploy/.deploy_env`（含 `SERVER_IP`、SSH 密钥或密码），且**已有一枚域名并完成 DNS 解析**（主域、www、app、api 四条 A 记录指向服务器 IP）：

1. 在 `deploy/.deploy_env` 中增加（或执行时传入）：
   - `SSL_DOMAIN=你的域名.com`
   - 可选：`CERTBOT_EMAIL=you@example.com`（接收证书到期提醒）

2. 本机执行：
   ```bash
   cd /path/to/clawjob
   bash deploy/ssl/setup-ssl-remote.sh
   ```

脚本会：同步 `deploy/` 到服务器 → 在服务器上安装 Nginx（若未安装）、certbot → 写入 Nginx 配置 → 申请证书并启用 HTTPS → 配置每月自动续期（crontab）。完成后按终端提示修改 `deploy/.env` 中的 API/前端地址为 https 并重新构建前端即可。

---

## 一、前置条件

1. **已有一枚域名**（如 `clawjob.com`），且 **DNS 已指向当前服务器**：
   - `clawjob.com` → 你的 ECS 公网 IP
   - `www.clawjob.com` → 同上
   - `app.clawjob.com` → 同上（任务大厅）
   - `api.clawjob.com` → 同上（后端 API）

   > Let's Encrypt 不支持为纯 IP 签发证书，必须使用域名。

2. **服务器已安装 Nginx**，且安全组/防火墙已放行 **80**、**443**。

3. **官网静态文件** 已在 `/var/www/clawjob-website`，**Docker 中任务大厅（3000）与后端（8000）** 已运行。

---

## 二、在服务器上执行（推荐 SSH 进入后执行）

### 方式 A：SSH 登录后在本机执行

```bash
# 1. SSH 登录
ssh -i 你的密钥.pem root@你的服务器IP

# 2. 进入项目并执行（将 your-domain.com 改为你的域名）
cd /opt/clawjob
DOMAIN=your-domain.com bash deploy/ssl/setup-letsencrypt.sh
```

可选：提供邮箱以接收证书到期提醒：

```bash
DOMAIN=your-domain.com CERTBOT_EMAIL=you@example.com bash deploy/ssl/setup-letsencrypt.sh
```

### 方式 B：本机一行命令（通过 SSH 传脚本）

```bash
cd /path/to/clawjob
ssh -i deploy/.deploy_env中配置的密钥 root@你的服务器IP "cd /opt/clawjob && DOMAIN=your-domain.com bash deploy/ssl/setup-letsencrypt.sh"
```

脚本会：

- 若未安装则安装 **certbot** 与 **python3-certbot-nginx**
- 用 `deploy/nginx/clawjob-ssl.conf` 生成 Nginx 配置（替换 `{{DOMAIN}}`）并写入 `/etc/nginx/conf.d/clawjob.conf`（或 `sites-available/clawjob`）
- 重载 Nginx
- 执行 **certbot --nginx** 为 `your-domain.com`、`www`、`app`、`api` 申请证书并自动配置 HTTPS、80→443 重定向

---

## 三、申请完成后

1. **确认 HTTPS 可访问**
   - 官网：https://your-domain.com
   - 任务大厅：https://app.your-domain.com
   - 后端 API：https://api.your-domain.com/health

2. **修改 deploy/.env（在服务器或本机部署用）**
   - `VITE_API_BASE_URL=https://api.your-domain.com`
   - `FRONTEND_URL=https://app.your-domain.com`
   - `CORS_ORIGINS=https://app.your-domain.com`
   - 若用 Google 登录：`GOOGLE_REDIRECT_URI=https://api.your-domain.com/auth/google/callback`

3. **重新构建并部署前端**（使 `VITE_API_BASE_URL` 生效）
   - 在服务器：`cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend`
   - 或本机用 `deploy/ensure-task-hall-on-server.sh` / `deploy-all.sh` 等按现有流程部署。

4. **官网「体验任务大厅」链接**
   - 用 `VITE_TASK_HALL_URL=https://app.your-domain.com` 重新构建并部署 clawjob-website（见 `deploy/deploy-website-only.sh`）。

5. **Google Cloud Console**（若用 Google 登录）
   - 在 OAuth 客户端中把「授权重定向 URI」改为 `https://api.your-domain.com/auth/google/callback`
   - 「已授权的 JavaScript 来源」中加入 `https://app.your-domain.com`

---

## 四、证书续期

Let's Encrypt 证书约 90 天有效。使用 `setup-letsencrypt.sh` 或 `setup-ssl-remote.sh` 时，**已自动添加** `/etc/cron.d/certbot-clawjob`（每月 1 日 03:00 执行 `certbot renew` 并重载 Nginx）。

手动续期：

```bash
sudo certbot renew
```

---

## 五、仅有一个域名时（子路径方式）

若你只有主域（如 `clawjob.com`）且不想用子域名，可改为路径方式：

- https://clawjob.com → 官网
- https://clawjob.com/app/ → 任务大厅（需 Nginx 反代到 3000，且前端需配置 base path）
- https://clawjob.com/api/ → 后端（需 Nginx 反代到 8000，且前端 API 基地址改为 `/api`）

路径方式需要改 Nginx 与前端配置，建议优先使用 **app / api 子域名** 方案（本脚本默认）。

---

## 六、故障排查

- **certbot 报错 domain not resolve / connection refused**  
  检查 DNS 是否已生效（`dig app.your-domain.com`），以及服务器 80 端口是否被占用、防火墙是否放行。

- **Nginx 报错 duplicate server name**  
  检查是否有多处配置同一 `server_name`，或禁用默认站点：`rm /etc/nginx/sites-enabled/default`。

- **HTTPS 正常但前端仍请求 http**  
  确认 `.env` 中 `VITE_API_BASE_URL` 已改为 `https://api.your-domain.com` 并已重新构建前端。

- **配置域名后，用 IP 访问 80 打不开 / 80 访问不了**  
  Nginx 只响应已配置的 `server_name`（域名），用 IP 访问时没有匹配的 server 块。已在新版 `deploy/nginx/clawjob-ssl.conf` 中增加 `default_server` 块，新部署会自动带上。**若你已配置过 SSL**，在服务器上追加默认 80 并重载即可：
  ```bash
  # 在服务器上执行（追加默认 80 块，使 http://你的IP 仍打开官网）
  sudo bash -c 'cat >> /etc/nginx/conf.d/clawjob.conf << "EOF"

# 默认 80：用 IP 或未匹配 Host 访问时仍可打开官网
server {
    listen 80 default_server;
    server_name _;
    root /var/www/clawjob-website;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
EOF'
  sudo nginx -t && sudo systemctl reload nginx
  ```
  （若使用 sites-available，则追加到 `/etc/nginx/sites-available/clawjob` 后执行 `sudo nginx -t && sudo systemctl reload nginx`。）
