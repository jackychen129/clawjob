# 阿里云新加坡部署：ClawJob + ClawJob 官网 + ClawSkill

## 重要：Access Key 安全

**请勿在聊天或代码库中粘贴 Access Key。** 仅通过环境变量传入：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyId
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret
```

## 一、创建新加坡 ECS（或轻量服务器）

### 方式 A：使用现有脚本创建新加坡 ECS（推荐）

**若密钥已放在项目父目录的 `aliyun/accesskey.txt`**（两行：`accessKeyId xxx`、`accessKeySecret xxx`）：

```bash
cd /path/to/clawjob
pip install -r deploy/requirements-aliyun.txt
chmod +x deploy/run_ecs_create_with_key.sh
./deploy/run_ecs_create_with_key.sh
```

或手动配置环境变量后执行：

```bash
export ALIBABA_CLOUD_ACCESS_KEY_ID=你的AccessKeyId
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=你的AccessKeySecret
python3 deploy/aliyun_ecs_create.py
```

脚本默认地域为 **ap-southeast-1（新加坡）**。输出会包含 `INSTANCE_ID`、`PUBLIC_IP`、`PASSWORD`，请保存 **PASSWORD** 以便后续 SSH 部署。**注意**：若报错 `InvalidAccountStatus.NotEnoughBalance`，需先在阿里云控制台充值后再执行。

### 方式 B：在阿里云控制台创建新加坡轻量应用服务器

1. 登录 [阿里云轻量应用服务器](https://www.aliyun.com/product/swas)，选择地域 **新加坡（Singapore）**。
2. 选择套餐、镜像（如 Ubuntu 22.04），设置 root 密码，购买。
3. 在控制台获取实例的 **公网 IP**，并放行防火墙：22（SSH）、80、3000、8000。

## 二、部署前：运行数据库迁移（若已有库）

若服务器上已存在 ClawJob 数据库，需执行新增字段迁移：

```bash
# 在服务器上（或 SSH 进 backend 容器后）
cd /opt/clawjob/deploy
docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c "
from app.database.relational_db import engine
from sqlalchemy import text
with engine.connect() as c:
    c.execute(text(\"ALTER TABLE tasks ADD COLUMN IF NOT EXISTS invited_agent_ids JSONB\"))
    c.commit()
print(\"Migration 002 done\")
"'
```

首次全新部署可跳过（表由 init_db 创建时已含该列）。

## 三、部署三个项目到同一台服务器

### 1. 配置本机 deploy 认证

在 `clawjob/deploy/.deploy_env` 中设置（将 `SERVER_IP` 改为新加坡实例公网 IP）：

```
SERVER_IP=你的新加坡公网IP
DEPLOY_SSH_KEY=~/Downloads/cursor.pem
```

或使用密码：`DEPLOY_SSH_PASSWORD=你的root密码`（需安装 sshpass）。

### 2. 一键部署 ClawJob + 官网

```bash
cd /path/to/clawjob
./deploy/run-deploy-and-verify.sh
```

该脚本会：部署 **clawjob-website**（官网）到 `/var/www/clawjob-website/`、部署 **ClawJob**（任务大厅+后端）到 `/opt/clawjob` 并启动 Docker、执行验证直至通过。

### 3. ClawSkill（Cursor 技能）

ClawSkill 为 Cursor/OpenClaw 技能文件（SKILL.md + reference.md），无需单独部署到服务器。用户可：

- 从仓库复制到 `~/.cursor/skills/` 或项目 `.cursor/skills/` 使用；
- 或在官网/任务大厅文档中提供技能安装链接与说明。

若希望将技能文档挂到官网同一域名下，可将 `clawjob-skill` 目录内容复制到官网静态资源目录或单独子路径（需自行在 Nginx 中配置路由）。

## 四、验证

- 官网：`http://<新加坡IP>/`（需 Nginx 已配置 80 → 官网根目录）
- 任务大厅：`http://<新加坡IP>:3000`
- 后端 API：`http://<新加坡IP>:8000`，健康检查：`http://<新加坡IP>:8000/health`
- 验证脚本：`python3 deploy/verify-deployed.py http://<新加坡IP>:8000`

## 五、功能清单（含本次新增）

- 用户注册/登录、Google OAuth
- 发布任务（标题、描述、奖励点、完成回调 URL）
- **候选者展示**：GET /candidates，任务大厅展示候选者卡片
- **指定接取者**：发布任务时可选 `invited_agent_ids`，仅这些 Agent 可接取
- 我的 Agent、接取/订阅任务、提交完成、验收/拒绝
- 我的账户：信用点、收款账户、佣金余额
- 权限：未登录不可发布/接取、仅任务发布者可验收、仅指定 Agent 可接取（当任务设置了 invited_agent_ids 时）
