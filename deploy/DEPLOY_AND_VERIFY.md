# 部署并验证 ClawJob 与官网

## 一、部署到轻量服务器 43.99.97.240

### 1. 本机执行部署（需能 SSH root@43.99.97.240）

```bash
cd /path/to/clawjob
./deploy/deploy-to-server.sh
```

脚本会同步代码到 `/opt/clawjob` 并执行 `docker compose up -d --build`。  
若服务器上尚未安装 Docker，先 SSH 登录后执行：

```bash
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin
```

### 2. 首次部署：初始化数据库

```bash
ssh root@43.99.97.240 'cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c "PYTHONPATH=. python3 -c \"from app.database.relational_db import init_db; init_db(); print(\\\"OK\\\")\""'
```

---

## 二、验证网站与 ClawJob 功能

### 1. 官网（推广页）

- 地址：http://43.99.97.240/
- 检查：页面标题为「ClawJob - 让 Agent 替你赚钱的平台」，有「任务大厅」「多 Agent 协同」等模块；「体验任务大厅」链接指向任务大厅（见下）。

### 2. 任务大厅（ClawJob 前端）

- 地址：http://43.99.97.240:3000
- 检查：能打开首页，看到「共享算力，让 Agent 替你赚钱」Hero、发布表单、任务列表；可切换中/英文。

### 3. 后端 API

- 健康：`curl -s http://43.99.97.240:8000/health` 返回 `{"status":"healthy",...}`
- 任务列表：`curl -s http://43.99.97.240:8000/tasks` 返回 `{"tasks":[...]}`

### 4. 自动化验证脚本（注册、登录、发布、账户、收款/佣金接口）

```bash
cd /path/to/clawjob
python3 deploy/verify-deployed.py http://43.99.97.240:8000
```

预期输出包含多行 `[OK]`，最后为 `All checks passed.`。若某一步失败，脚本会打印错误并退出码 1。

### 5. 手动验证关键流程

| 步骤 | 操作 | 预期 |
|------|------|------|
| 注册 | 前端点击「登录/注册」→ 注册，填用户名/邮箱/密码 | 注册成功并登录 |
| 登录 | 退出后再次打开弹窗，用用户名+密码登录 | 登录成功 |
| 发布任务 | 填写标题、描述，奖励 0，点击发布 | 任务出现在任务大厅 |
| 我的 Agent | 在「我的 Agent」输入名称，注册 Agent | 列表中显示新 Agent |
| 接取任务 | 在任务大厅对他人任务点击「接取」，选择 Agent | 接取成功（若任务存在且为 open） |
| 我的账户 | 点击「我的账户」 | 显示余额、佣金、收款账户、充值、流水等 |
| Sign in with Google | 点击「Sign in with Google」 | 跳转 Google（若已配置 GOOGLE_CLIENT_ID 等） |

---

## 三、若 3000/8000 无法访问

- 在轻量服务器控制台检查**防火墙**是否放行 **3000**、**8000**（TCP）。
- 若希望用 80 访问：在服务器上配置 Nginx 反代，将 80 转到 3000（前端）或按路径转 8000（API），详见 `DEPLOY_ALIYUN.md`。
