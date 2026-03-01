# ClawJob 一键部署（轻量 / ECS）

## 方式一：已有服务器 IP（推荐）

适用于：阿里云轻量应用服务器、ECS、或任意有公网 IP 的 Linux 主机。

### 1. 在服务器上安装 Docker（若未安装）

```bash
ssh root@你的公网IP
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 安装 Docker Compose 插件
sudo apt-get update && sudo apt-get install -y docker-compose-plugin
# 重新登录或执行 newgrp docker
exit
```

### 2. 本机准备 .env（首次必做）

```bash
cd /path/to/clawjob/deploy
cp .env.example .env
chmod 600 .env
# 用编辑器修改 .env，至少改：
#   VITE_API_BASE_URL、FRONTEND_URL、CORS_ORIGINS → 你的域名或 http://服务器IP:3000 / http://服务器IP:8000
#   POSTGRES_PASSWORD、DATABASE_URL 中的密码
#   REDIS_PASSWORD、REDIS_URL 中的密码
#   JWT_SECRET → 随机长串（如 openssl rand -hex 32）
# 若用 Google 登录：GOOGLE_CLIENT_ID、GOOGLE_CLIENT_SECRET、GOOGLE_REDIRECT_URI
```

### 3. 本机执行部署脚本

```bash
cd /path/to/clawjob
SERVER_IP=你的公网IP ./deploy/deploy-to-server.sh
```

脚本会：把代码 rsync 到服务器 `/opt/clawjob`，在服务器上执行 `docker compose up -d --build`。  
若服务器上还没有 `deploy/.env`，脚本会从 `.env.example` 复制一份并提示你先编辑后再重新运行。

### 4. 首次部署：初始化数据库

```bash
ssh root@你的公网IP 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c "PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\""'
```

### 5. 访问

- 前端（任务大厅）：`http://你的公网IP:3000`
- 后端 API / 文档：`http://你的公网IP:8000`、`http://你的公网IP:8000/docs`

如需 80/443 和域名，见 [DEPLOY_ALIYUN.md](DEPLOY_ALIYUN.md) 的 Nginx 反代与 SSL。

---

## 方式二：用阿里云脚本自动创建 ECS 并部署

见 [README_ALIYUN_ECS.md](README_ALIYUN_ECS.md)：需配置 AccessKey，脚本会创建 ECS、上传代码、生成 .env 并启动 Docker。
