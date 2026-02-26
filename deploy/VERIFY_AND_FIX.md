# 部署后验证与常见问题修复

## 线上环境完全不工作时的排查顺序

若从外网访问官网 / 任务大厅 / API 全部超时或无法打开，按以下顺序做：

### 步骤 1：在服务器本机做诊断（必做）

SSH 登录服务器后执行（或本机执行下面一行，把脚本通过 SSH 在服务器上跑）：

```bash
ssh root@43.99.97.240 'bash -s' < deploy/verify-on-server.sh
```

或在服务器上：

```bash
bash /opt/clawjob/deploy/verify-on-server.sh
```

脚本会输出：Docker 容器状态、本机 80/3000/8000 端口、后端 /health、任务大厅与官网 HTTP 状态、以及本机 API 全流程校验结果。

- **若本机 80/3000/8000 都正常**：多半是云厂商防火墙未放行。到阿里云轻量控制台 → 该实例 → 防火墙，放行 **TCP 80、3000、8000**，来源 0.0.0.0/0。
- **若本机某端口失败**：根据脚本输出修容器或 Nginx（见下方「错误与修复对照」），修完再跑一次本脚本。

### 步骤 2：本机验证并自动修复（能 SSH 到服务器时）

在本机执行「一键：验证并自动修复直到通过」，脚本会从本机请求线上 API；若超时则会 SSH 到服务器启动/重建容器并重试。

### 任务大厅（:3000）访问不了

1. **先确认防火墙**：阿里云轻量控制台 → 该实例 → 防火墙 → 添加入站规则 **TCP 3000、8000**，来源 0.0.0.0/0。
2. **一键检查并修复（推荐）**：在本机执行（需能 SSH 到服务器）：
   ```bash
   cd /path/to/clawjob && bash deploy/check-and-fix-online.sh
   ```
   脚本会：检查外网 3000/8000 可达性 → SSH 看容器与 .env → 若容器未跑则启动/重建 → 跑完 API 验证（verify-deployed.py）。
3. **仅启动任务大厅**：若只需把前端/后端拉起来：
   ```bash
   cd /path/to/clawjob && bash deploy/fix-task-hall.sh
   ```
4. **页面能开但接口报错 / 白屏**：多半是前端构建时 API 地址不对。在服务器上确认 `deploy/.env` 有：
   - `VITE_API_BASE_URL=http://你的公网IP:8000`
   - `CORS_ORIGINS=http://你的公网IP:3000`
   然后重建前端：`docker compose -f docker-compose.prod.yml up -d --build frontend`，并重启后端使 CORS 生效。

### 步骤 3：确认官网「体验任务大厅」链接

若官网能打开但点击「体验任务大厅」跳错或打不开：

- 重新部署官网（会注入正确的任务大厅地址）：  
  `SERVER_IP=43.99.97.240 ./clawjob/deploy/deploy-all.sh`
- 若未重新部署，官网代码已支持「同站运行时回退」：从 `http://你的IP/` 打开时，链接会自动变为 `http://你的IP:3000`，部署最新官网后即可生效。

---

## 一键：验证并自动修复直到通过（推荐）

在本机（能 SSH 到服务器的环境）执行：

```bash
cd /path/to/clawjob
chmod +x deploy/verify-and-fix-until-pass.sh
./deploy/verify-and-fix-until-pass.sh
```

脚本会：运行验证 → 若失败则按错误类型 SSH 到服务器做修复（启动容器 / init_db / 配置 CORS）→ 再次验证，最多重复 5 次，直到 **All checks passed** 或无法自动修复。

---

## 仅验证（不自动修复）

```bash
python3 deploy/verify-deployed.py http://43.99.97.240:8000
```

结果会打印到终端并写入 `deploy/verify-result.txt`。若出现错误，可按下表排查。

## 错误与修复对照

| 现象 | 可能原因 | 修复方法 |
|------|----------|----------|
| 请求超时 (timed out) | 防火墙未放行或服务未启动 | 1) 阿里云轻量控制台 → 防火墙 → 放行 TCP 80、3000、8000<br>2) SSH 登录服务器执行 `docker ps`，确认 backend、frontend 为 Up；若未起则 `cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml up -d` |
| /health 返回 500 | 数据库未初始化或依赖服务不可用 | 在服务器上执行：<br>`cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c "from app.database.relational_db import init_db; init_db(); print(\"OK\")"'` |
| 后端启动即退出 (RuntimeError: JWT_SECRET / CORS_ORIGINS) | 生产校验未通过 | 在 `deploy/.env` 中设置：<br>• `JWT_SECRET` 为强随机字符串（非默认值）<br>• `CORS_ORIGINS` 为前端地址，如 `http://43.99.97.240:3000`（逗号分隔，禁止 `*`）<br>然后重启：`docker compose -f docker-compose.prod.yml up -d backend` |
| 前端请求 API 被 CORS 拒绝 | CORS_ORIGINS 未包含前端来源 | 在 `deploy/.env` 中设置 `CORS_ORIGINS=http://43.99.97.240:3000`（或你的前端域名），重启 backend |
| 注册/登录 401 或 422 | 请求体格式或 JWT 配置问题 | 确认 `deploy/.env` 中 `JWT_SECRET` 已设置；检查请求体是否包含 username/email/password（注册）、username/password（登录） |

## 在服务器上快速自检

SSH 登录后执行：

```bash
# 容器是否在跑
docker ps

# 后端健康（在服务器本机）
curl -s http://localhost:8000/health | head -c 500

# 若需重新初始化数据库
cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c "from app.database.relational_db import init_db; init_db(); print(\"OK\")"'
```

修复后再次运行验证脚本，直到全部通过。
