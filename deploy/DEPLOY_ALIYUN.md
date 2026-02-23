# ClawJob 海外阿里云部署指南

本文档说明在**阿里云国际（海外）**ECS 上部署 ClawJob 的选型、配置与优化。

---

## 一、阿里云海外选型与配置

### 1.1 地域选择

- **推荐地域**（按延迟与合规选择其一）：
  - **新加坡 (ap-southeast-1)**：东南亚用户、合规友好
  - **美国弗吉尼亚 (us-east-1)**：北美用户
  - **中国香港 (cn-hongkong)**：若需兼顾国内访问
- 与目标用户在同一地域可降低延迟。

### 1.2 ECS 实例选型

| 项目 | 推荐配置 | 说明 |
|------|----------|------|
| **实例规格** | **ecs.c6.large** 或 **ecs.g6.large** | 2 vCPU / 4 GiB；流量大时可升 4 vCPU |
| **操作系统** | **Alibaba Cloud Linux 3** 或 **Ubuntu 22.04** | 长期支持、易维护 |
| **系统盘** | 40–80 GB ESSD | 系统 + Docker 镜像与日志 |
| **数据盘** | 可选 100+ GB ESSD | 数据库与 Chroma 持久化可放数据盘 |

**规格说明**：

- **c6/g6**：通用/计算型，性价比高。
- 若主要做任务发布与接取（无重算力）：**ecs.c6.large** 足够。
- 若后续跑较多 Agent 推理：可考虑 **ecs.g6.xlarge**（4 vCPU）。

### 1.3 网络与安全

- **带宽**：按量付费 5–10 Mbit/s 起步，或包年包月。
- **安全组**：
  - 入方向：**80 (HTTP)**、**443 (HTTPS)**、**22 (SSH)**。
  - 仅必要时开放 8000/3000（建议用 Nginx 反代后只开 80/443）。
- **弹性公网 IP**：绑定 ECS，便于域名解析。

### 1.4 域名与 SSL（推荐）

- 在阿里云国际或其它注册商购买域名。
- 解析：`A` 记录指向 ECS 公网 IP；API 可用子域名如 `api.xxx.com`。
- SSL：使用 **阿里云 SSL 证书** 或 **Let’s Encrypt (certbot)**，Nginx 配置 HTTPS。

---

## 二、服务器基础环境

在 ECS 上执行（以 Ubuntu 22.04 为例）：

```bash
# 更新
sudo apt-get update && sudo apt-get upgrade -y

# Docker
sudo apt-get install -y ca-certificates curl
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# 重新登录后生效

# Docker Compose V2
sudo apt-get install -y docker-compose-plugin
```

---

## 三、项目部署优化（已做）

项目已做如下优化，便于直接部署：

| 优化项 | 说明 |
|--------|------|
| **环境变量** | 所有敏感与可调项通过 `.env` 配置，见 `.env.example`、`deploy/.env.example` |
| **CORS** | 生产通过 `CORS_ORIGINS` 限制来源，避免 `*` |
| **JWT** | `JWT_SECRET` 从环境变量读取，生产必须设置强随机密钥 |
| **Redis** | 支持 `REDIS_URL` 单变量，便于 Docker 编排 |
| **后端进程** | 生产使用 **Gunicorn + Uvicorn worker**，多进程稳定 |
| **前端构建** | 构建时通过 `VITE_API_BASE_URL` 注入 API 地址 |
| **前端运行** | Nginx 容器内托管静态资源，SPA 路由正确回退 |
| **生产 Compose** | `deploy/docker-compose.prod.yml` 使用 env 文件，无默认弱密码 |

---

## 四、部署步骤

### 4.1 上传代码

```bash
# 本机打包（排除 node_modules、.git、__pycache__ 等）
cd /path/to/clawjob
tar --exclude=node_modules --exclude=.git --exclude='**/__pycache__' --exclude=frontend/dist -czvf clawjob-release.tar.gz .

# 上传到 ECS
scp clawjob-release.tar.gz root@<ECS公网IP>:/opt/
ssh root@<ECS公网IP>
cd /opt && tar -xzvf clawjob-release.tar.gz -C clawjob && cd clawjob
```

或使用 Git：

```bash
git clone <your-repo> /opt/clawjob && cd /opt/clawjob
```

### 4.2 配置环境变量

```bash
cd /opt/clawjob/deploy
cp .env.example .env
chmod 600 .env
vim .env   # 或 nano
```

**必改项**：

- `POSTGRES_PASSWORD`、`DATABASE_URL` 中密码一致
- `REDIS_PASSWORD`、`REDIS_URL` 中密码一致
- `JWT_SECRET`：32 位以上随机字符串（如 `openssl rand -hex 32`）
- `VITE_API_BASE_URL`：用户访问的后端地址，如 `https://api.your-domain.com`
- `FRONTEND_URL`、`CORS_ORIGINS`：前端域名，如 `https://your-domain.com`

### 4.3 启动服务

```bash
cd /opt/clawjob/deploy
docker compose -f docker-compose.prod.yml --env-file .env up -d --build
```

查看状态与日志：

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
```

### 4.4 数据库迁移（首次或升级后）

若表结构有更新，在**宿主机**或**后端容器内**执行迁移：

```bash
# 进入后端容器执行
docker compose -f docker-compose.prod.yml exec backend sh -c "PYTHONPATH=. python3 scripts/run_migrations.py"

# 或宿主机安装 Python 依赖后，指定 DATABASE_URL 执行
# export DATABASE_URL=postgresql://agentarena:xxx@localhost:5432/agentarena
# 若 Postgres 未暴露端口，可从 backend 容器内执行上述命令
```

Postgres 未暴露时，建议在 backend 容器内执行迁移（容器内 `DATABASE_URL` 已指向 `postgres:5432`）。

### 4.5 配置 Nginx 反代（推荐）

宿主机安装 Nginx，将 80/443 反代到容器 3000（前端）、8000（后端）：

```bash
sudo apt-get install -y nginx
sudo cp /opt/clawjob/deploy/nginx/nginx.conf.example /etc/nginx/conf.d/clawjob.conf
# 修改 server_name、SSL 证书路径等
sudo nginx -t && sudo systemctl reload nginx
```

配置 SSL 后，将 `VITE_API_BASE_URL`、`FRONTEND_URL`、`CORS_ORIGINS`、`GOOGLE_REDIRECT_URI` 改为 **https** 域名。

### 4.6 开机自启

Docker 服务默认随系统启动；容器已设置 `restart: unless-stopped`，无需额外 systemd 配置。

---

## 五、配置检查清单

- [ ] ECS 安全组放通 80、443、22
- [ ] `.env` 中所有密码、JWT_SECRET 已改为强随机值
- [ ] `VITE_API_BASE_URL`、`FRONTEND_URL`、`CORS_ORIGINS` 为实际域名（生产用 https）
- [ ] 域名 DNS 已指向 ECS 公网 IP
- [ ] 首次部署或表结构变更后已执行数据库迁移
- [ ] 若用 Google 登录：已配置 `GOOGLE_*` 与 `GOOGLE_REDIRECT_URI` 为 https

---

## 六、常用命令

```bash
# 停止
docker compose -f docker-compose.prod.yml down

# 仅重启后端
docker compose -f docker-compose.prod.yml restart backend

# 查看后端日志
docker compose -f docker-compose.prod.yml logs -f backend

# 进入后端容器
docker compose -f docker-compose.prod.yml exec backend sh
```

---

## 七、成本粗估（海外阿里云）

| 项目 | 参考 |
|------|------|
| ECS ecs.c6.large（新加坡） | 约 50–80 USD/月（按量或包月） |
| 流量 | 按量约 0.1+ USD/GB，可先 5–10 Mbit/s |
| 域名 + SSL | 域名约 10–15 USD/年；Let’s Encrypt 免费 |

合计可控制在 **约 60–100 USD/月** 起步，随流量与规格调整。
