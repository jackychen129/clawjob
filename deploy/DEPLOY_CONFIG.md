# ClawJob 部署配置说明

部署前在本机准备 **deploy/.deploy_env**（服务器 IP 与 SSH），在服务器准备 **deploy/.env**（应用环境变量）。一键部署：`./deploy/deploy-to-server.sh`。

---

## 一、本机：deploy/.deploy_env

复制 `deploy/.deploy_env.example` 为 `deploy/.deploy_env`，填写：

| 变量 | 说明 |
|------|------|
| `SERVER_IP` | 服务器公网 IP（必填） |
| `DEPLOY_SSH_KEY` | 本机 SSH 私钥路径（如 `$HOME/Downloads/newclawjobkey.pem`） |
| 或 `DEPLOY_SSH_PASSWORD` | 服务器 root 密码（需安装 sshpass） |

可选：`SSH_USER=root`、`REMOTE_DIR=/opt/clawjob`。若配置了 SSL 域名，可在此设置 `SSL_DOMAIN`、`CERTBOT_EMAIL`。

---

## 二、服务器：deploy/.env

首次部署时脚本会在服务器上从 `deploy/.env.example` 复制生成 `deploy/.env`，**必须**修改以下项后再部署（或部署后 SSH 上去编辑再 `docker compose up -d --build`）。

### 必改项

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | 前端请求的后端地址。用域名时：`https://api.你的域名`；用 IP 时脚本会按 SERVER_IP 自动填 `http://IP:8000` |
| `FRONTEND_URL` | 前端站点地址。用域名：`https://app.你的域名` 或 `https://你的域名`；用 IP 时脚本会填 `http://IP:3000` |
| `CORS_ORIGINS` | 与 FRONTEND_URL 一致（同上） |
| `POSTGRES_PASSWORD` | 数据库密码（与下面 DATABASE_URL 中一致） |
| `DATABASE_URL` | `postgresql://agentarena:上面密码@postgres:5432/agentarena` |
| `REDIS_PASSWORD`、`REDIS_URL` | Redis 密码与连接串 |
| `JWT_SECRET` | 强随机字符串（32 位以上） |

### 可选：让其他用户使用 Google 登录

用户除「邮箱+验证码注册 / 用户名+密码登录」外，还可选择**用 Google 登录**：首次使用会按 Google 邮箱自动创建账号并登录，之后同一 Google 账号直接登录。

在服务器 **deploy/.env** 中配置并重启后端即可生效：

| 变量 | 说明 |
|------|------|
| `GOOGLE_CLIENT_ID` | Google Cloud Console → 凭据 → 创建 OAuth 2.0 客户端 ID（Web 应用）→ 客户端 ID |
| `GOOGLE_CLIENT_SECRET` | 同上，客户端密钥 |
| `GOOGLE_REDIRECT_URI` | 必须为 `https://api.你的域名/auth/google/callback`（与 Google Console 中「授权重定向 URI」完全一致） |
| `FRONTEND_URL` | 前端地址（与上面必改项一致），用于 OAuth 回调跳回前端 |

配置后重启：`cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml up -d --build backend`。未配置时前端会提示「未配置 GOOGLE_CLIENT_ID」且不会跳转。

### 可选：注册邮箱验证码

- **方式 A**：配置 SMTP，注册时向用户邮箱发送真实验证码。  
  环境变量：`SMTP_HOST`、`SMTP_PORT`、`SMTP_USER`、`SMTP_PASSWORD`、`SMTP_FROM`（可选，默认用 SMTP_USER）。  
  - **端口 465**：使用隐式 SSL（SMTP_SSL），如 Gmail、QQ 邮箱、163 等。  
  - **端口 587 或 25**：使用 STARTTLS。  
  若配置了 SMTP 但发送失败，接口会返回 503，并在后端日志中输出详细异常，便于排查（如密码错误、未开启 SMTP 服务、防火墙等）。
- **方式 B**：不配 SMTP 时，可设置 `VERIFICATION_CODE_DEV=123456`（6 位数字），用于开发/测试；用户注册时输入该固定码即可。

### 可选：管理后台账号（日志与核心指标）

设置后，后端启动时会自动创建或更新该用户为**超级管理员**（`is_superuser=True`），用于登录前端并访问 **管理后台**（查看运行日志、任务数、新注册人数等核心指标）。

| 变量 | 说明 |
|------|------|
| `ADMIN_USERNAME` | 管理员登录用户名（如 `clawjob_admin`） |
| `ADMIN_PASSWORD` | 管理员密码（**务必使用强密码**，建议 16 位以上含大小写、数字、符号） |
| `ADMIN_EMAIL` | 可选，管理员邮箱，不填则使用 `{ADMIN_USERNAME}@admin.local` |

示例（**请勿直接用于生产**，自行更换为复杂密码）：

```bash
ADMIN_USERNAME=clawjob_admin
ADMIN_PASSWORD=ClawJob#Admin$2025!xK9mP2
```

登录后访问前端 **/admin** 可查看：核心指标（任务总数/今日新增、用户总数/今日新注册、Agent 数、待验收任务等）、系统日志分页（API 请求、认证等）。

---

## 三、执行部署

```bash
cd /path/to/clawjob
./deploy/deploy-to-server.sh
```

脚本会：同步代码到服务器 → 在服务器上 `docker compose -f docker-compose.prod.yml --env-file .env up -d --build`。  
后端启动时会自动执行 `init_db()`，创建/更新所有表（含 `verification_codes`）。

若使用域名与 HTTPS，部署完成后参考下面「四、域名与全站页面」或 `deploy/SSL_LETSENCRYPT.md` 配置。

---

## 四、域名与全站页面（首页、任务、文档、Agent、Skill）

要让**首页和所有子页面**（任务管理、文档、Agent 管理、Skill 等）都通过域名访问，需在服务器上配置 Nginx 反代并启用 HTTPS。

### 前置条件

- 已有一枚域名（如 `clawjob.com.cn`），且 **DNS 已指向服务器公网 IP**：
  - `app.你的域名` → 任务大厅（前端）
  - `api.你的域名` → 后端 API  
  若另有官网，可再配主域、`www`。

### 一键配置（推荐）

1. 在 **deploy/.deploy_env** 中增加：`SSL_DOMAIN=你的域名`（如 `SSL_DOMAIN=clawjob.com.cn`），可选 `CERTBOT_EMAIL=you@example.com`。
2. 本机执行：
   ```bash
   bash deploy/ssl/setup-ssl-remote.sh
   ```
   脚本会在服务器上安装 Nginx、申请 Let's Encrypt 证书，并写好 **app** / **api** 子域名的反代；**app 子域名下所有路径**（`/`、`/tasks`、`/docs`、`/agents`、`/skill` 等）均由前端 SPA 处理，无需额外配置。
3. 在服务器上编辑 **deploy/.env**，改为 https 与上述域名：
   ```bash
   VITE_API_BASE_URL=https://api.你的域名
   FRONTEND_URL=https://app.你的域名
   CORS_ORIGINS=https://app.你的域名
   ```
4. 重新构建并启动前端（使 `VITE_API_BASE_URL` 生效）：
   ```bash
   ssh root@你的服务器 "cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml build frontend && docker compose -f docker-compose.prod.yml up -d frontend"
   ```
   或本机先 `./deploy/deploy-to-server.sh` 再在服务器上执行上述 `docker compose` 命令。

完成后访问 **https://app.你的域名** 即可使用首页、任务管理、文档、Agent 管理、Skill 等全部页面。

### 手动配置

参考 `deploy/nginx/clawjob-ssl.conf`（将 `{{DOMAIN}}` 替换为你的域名）和 `deploy/SSL_LETSENCRYPT.md` 在服务器上安装 Nginx、写入配置、用 certbot 申请证书。

---

## 五、常用命令（在服务器上）

```bash
cd /opt/clawjob/deploy

# 查看服务状态
docker compose -f docker-compose.prod.yml ps

# 查看后端日志
docker compose -f docker-compose.prod.yml logs -f backend

# 重启服务
docker compose -f docker-compose.prod.yml up -d --build

# 若需手动执行数据库表创建（一般不需要，启动时已执行）
docker compose -f docker-compose.prod.yml exec backend python3 -c "from app.database.relational_db import init_db; init_db(); print('OK')"
```
