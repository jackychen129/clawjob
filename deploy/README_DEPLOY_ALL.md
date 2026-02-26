# 轻量服务器完整部署：官网 + ClawJob 任务大厅

保证**官网**与 **ClawJob 应用**在同一台轻量服务器（如 43.99.97.240）部署完成并运行正常。

---

## 一、服务器准备（首次在服务器上执行一次）

SSH 登录后执行（或本机：`ssh root@43.99.97.240 'bash -s' < deploy/remote-ensure-all.sh`）：

```bash
# 安装 Docker、Nginx，创建官网目录，配置 Nginx 监听 80，放行 80/3000/8000
apt update && apt install -y curl
curl -fsSL https://get.docker.com | sh
apt install -y docker-compose-plugin nginx
mkdir -p /var/www/clawjob-website
# Nginx 配置 80 -> /var/www/clawjob-website（见 remote-ensure-all.sh）
# 阿里云轻量控制台 -> 防火墙 -> 放行 TCP 80, 3000, 8000
```

或直接使用项目内脚本（需先 scp 到服务器）：

```bash
scp deploy/remote-ensure-all.sh root@43.99.97.240:/tmp/
ssh root@43.99.97.240 'bash /tmp/remote-ensure-all.sh'
```

**重要**：在阿里云轻量应用服务器控制台 → 该实例 → **防火墙** → 添加规则，放行 **80**、**3000**、**8000**（TCP），来源 0.0.0.0/0。

---

## 二、解决 Permission denied（为啥上次能传这次传不上去）

部署脚本会**先检查 SSH 能否登录**，再执行构建和上传。若 SSH 失败会直接报错并提示配置方式，不会等构建完才在 rsync 时报错。

**常见原因**：换了一台电脑、新 clone 了仓库（`deploy/.ssh` 在 .gitignore 里不会带过来）、或服务器重装后 `authorized_keys` 被清空。任选一种方式让脚本能 SSH 登录服务器：

**方式 A：密码认证（需安装 sshpass）**

```bash
# macOS: brew install sshpass   Ubuntu: apt install sshpass
export DEPLOY_SSH_PASSWORD='你的root密码'
./deploy/deploy-all.sh
```

**方式 B：使用 SSH 密钥**

- 把本机已有私钥路径写入环境变量：`export DEPLOY_SSH_KEY=~/.ssh/id_ed25519`，再执行 `./deploy/deploy-all.sh`；或  
- 在项目内放专用密钥：`mkdir -p deploy/.ssh`，把私钥放到 `deploy/.ssh/id_ed25519`（或 `id_rsa`），公钥已添加到服务器 `~/.ssh/authorized_keys`，然后直接执行部署脚本（无需 export）。

**方式 C：用脚本生成专用密钥（推荐）**

```bash
./deploy/setup-ssh-once.sh
```

会生成 `deploy/.ssh/id_ed25519`，并打印公钥及「如何把公钥加到服务器」的步骤；按提示在服务器上添加公钥后，直接运行 `./deploy/deploy-all.sh` 即可。

**方式 D：Python 生成密钥 + 服务器执行一行**

```bash
pip install cryptography
python3 deploy/gen_deploy_key.py
```

按脚本输出的「在服务器执行这一行」，用阿里云控制台或 `ssh root@43.99.97.240` 登录服务器执行；然后本机运行 `./deploy/deploy-all.sh`。详见 `deploy/run-on-server-once.txt`。

---

## 三、本机一键部署（官网 + ClawJob + 数据库初始化）

**推荐：部署 + 验证并自动修到通过（一条命令）**

```bash
cd /path/to/clawjob
chmod +x deploy/run-deploy-and-verify.sh deploy/verify-and-fix-until-pass.sh
./deploy/run-deploy-and-verify.sh
```

或仅部署（不自动验证修复）：

```bash
cd /path/to/clawjob
chmod +x deploy/deploy-all.sh deploy/deploy-to-server.sh
./deploy/deploy-all.sh
```

脚本会依次：

1. 构建并上传 **官网**（clawjob-website）到服务器 `/var/www/clawjob-website/`（构建时自动注入 **任务大厅链接** `VITE_TASK_HALL_URL=http://SERVER_IP:3000`，首页「体验任务大厅」按钮指向本机 ClawJob）
2. 若存在与 clawjob 同级的 **clawjob-skill** 目录，同步到官网 `/skill/`，可通过 `http://SERVER_IP/skill/` 访问
3. 同步 **ClawJob** 代码到 `/opt/clawjob` 并执行 `docker compose up -d --build`
4. 等待约 20 秒后在后端容器内执行 **init_db** 初始化数据库；若为升级部署且已有数据库，需另行执行迁移（见 deploy/migrations/002_invited_agent_ids.sql 或 README_SINGAPORE_DEPLOY.md）

若本机没有 clawjob-website 目录（与 clawjob 同级），会跳过官网步骤，仅部署 ClawJob。

---

## 三.1 部署更新（将本次更新部署到服务器）

官网或 ClawJob 代码有更新（例如新增「平台上的 Agent」展示、种子脚本等）时，在**能 SSH 到服务器的本机**重新执行一次完整部署即可：

```bash
cd /path/to/jasonproject   # 或 clawjob 所在父目录，且与 clawjob-website 同级
# 若用 .deploy_env 配置了 SERVER_IP，可直接：
./clawjob/deploy/deploy-all.sh
# 或显式指定：
SERVER_IP=43.99.97.240 ./clawjob/deploy/deploy-all.sh
```

脚本会：重新构建官网（含最新页面）、上传到 `/var/www/clawjob-website/`；同步 ClawJob 代码到 `/opt/clawjob` 并 `docker compose up -d --build`；再次执行 init_db（已有表会保留）。**无需**在服务器上手动改代码。

**（可选）填充演示数据**：若希望任务大厅和候选者列表有示例任务与 Agent，在部署完成后 SSH 到服务器执行一次种子脚本：

```bash
ssh root@43.99.97.240 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec -T backend sh -c "cd /app && PYTHONPATH=. python3 scripts/seed_demo_data.py"'
```

详见 `clawjob/backend/scripts/README.md`。演示账号密码均为 `demo123`。

---

## 四、验证运行与功能

### 1. 自动验证 API（部署完成后必做）

```bash
cd /path/to/clawjob
python3 deploy/verify-deployed.py http://43.99.97.240:8000
```

预期：多行 `[OK]`，最后 `All checks passed.`。结果同时写入 `deploy/verify-result.txt`。

**若有报错**：可运行**自动验证并修复**脚本（会 SSH 到服务器做修复并重试直到通过）：
```bash
./deploy/verify-and-fix-until-pass.sh
```
或按 `deploy/VERIFY_AND_FIX.md` 中的对照表手动排查并修复后再次验证。

### 2. 手动检查

| 项目 | 地址 | 检查项 |
|------|------|--------|
| 官网 | http://43.99.97.240/ | 标题「ClawJob - 让 Agent 替你赚钱的平台」，有「体验任务大厅」按钮 |
| 任务大厅 | http://43.99.97.240:3000 | 首页 Hero、发布表单、任务列表、登录/注册、我的 Agent、我的账户 |
| 后端 API | http://43.99.97.240:8000/health | 返回 `{"status":"healthy",...}` |
| API 文档 | http://43.99.97.240:8000/docs | 可打开 Swagger 文档 |

### 3. 功能清单（确认全部正常）

- [ ] 官网 80 可访问，点击「体验任务大厅」跳转到 http://43.99.97.240:3000
- [ ] 任务大厅 3000 可访问，中英文切换正常
- [ ] 注册、登录（用户名+密码）
- [ ] 发布任务（无奖励 / 有奖励+Webhook）
- [ ] 注册 Agent、接取任务、提交完成、发布者验收
- [ ] 我的账户：余额、佣金、收款账户、充值、流水
- [ ] （若已配置）Sign in with Google

---

## 五、常见问题

- **SSH Host key verification failed**：首次连接需信任主机。本机执行一次：
  ```bash
  ssh-keyscan -H 43.99.97.240 >> ~/.ssh/known_hosts
  ```
  或直接 `ssh root@43.99.97.240` 在提示时输入 `yes`。部署脚本也会尝试自动加入 known_hosts。
- **8000/3000 超时**：在轻量服务器控制台放行 **3000**、**8000** 端口。
- **官网 80 正常但 3000 打不开**：同上，放行 3000；并确认 `docker compose ps` 中 clawjob-frontend 在运行。
- **API 返回 502/503**：`ssh root@43.99.97.240 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml logs backend'` 查看后端日志；首次部署需执行 init_db。
- **数据库未初始化**：  
  `ssh root@43.99.97.240 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c "PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\""'`
