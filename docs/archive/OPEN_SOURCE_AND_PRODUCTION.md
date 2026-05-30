# 开源仓库与线上环境指向说明

本文说明如何将 ClawJob（含 Skill 与后端）以开源方式托管在 GitHub，以及如何让现有线上环境指向该开源仓库。

## 一、开源仓库包含与排除

### 包含内容

- **后端**：`backend/`（FastAPI、任务/Agent/认证等）
- **前端**：`frontend/`（Vue 3 任务大厅、Skill 页等）
- **Skill**：`skills/`（clawjob 技能及加载说明）
- **文档**：`README.md`、`docs/`、各模块 README
- **部署参考**：`deploy/` 下通用配置（如 `docker-compose.prod.yml`、`.env.example`、`migrations/`）；不含机器专属脚本与密钥

### 不包含（已通过 .gitignore 排除）

- **隐私与密钥**：`*.pem`、`deploy/.deploy_env`、`.env`、`deploy/.env` 等
- **临时/调试脚本**：`tools/e2e_browser_click.py`、`tools/e2e_browser_page_test.py`、`tools/browser_flow_test.py`、`tools/*_debug*`
- **部署产出与日志**：`deploy/*.txt`、`deploy/*.bak*`、`deploy/data/`、`deploy/.ssh/` 等

如需进一步排除「特殊部署脚本」（含固定 IP、内网路径的脚本），可在本地将对应文件加入 `.gitignore` 或从仓库中移除后再推送到公开仓库。

## 二、在 GitHub 创建新仓库并推送

### 1. 在 GitHub 上创建新仓库

- 登录 GitHub → New repository
- 仓库名建议：`clawjob`（或 `clawjob-platform`）
- 选择 Public，不勾选 “Add a README”（本地已有）
- 记下仓库 URL；当前开源仓库为：`https://github.com/jackychen129/clawjob.git`

### 2. 本地添加远程并推送

在项目根目录（clawjob）执行：

```bash
# 确认当前远程
git remote -v

# 添加新的开源仓库为远程（名称可自定，如 open）
git remote add open https://github.com/jackychen129/clawjob.git

# 推送 main（或当前默认分支）
git push -u open main
```

若希望开源仓库与现有私有仓库分支一致，可先 `git pull` 再 `git push open main`。

### 3. 使用 GitHub CLI 创建并推送（可选）

若已安装 `gh` 且已登录：

```bash
gh repo create clawjob --public --source=. --remote=open --push
```

将 `clawjob` 和 `--source=.` 按实际组织/路径修改。

## 三、让线上环境指向新的开源仓库

### 方式 A：线上服务器从新仓库拉取

1. SSH 登录到当前部署 ClawJob 的服务器。
2. 进入应用目录（如 `/opt/clawjob`）。
3. 将 git 远程改为新的开源仓库并拉取：

```bash
cd /opt/clawjob
git remote set-url origin https://github.com/jackychen129/clawjob.git
git fetch origin
git checkout main   # 或你使用的分支
git pull origin main
```

4. 按现有流程重建/重启（如 Docker）：

```bash
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
```

5. 环境变量（如 `DATABASE_URL`、`JWT_SECRET`）仍在服务器本地配置（`deploy/.env` 等），不要从仓库覆盖；若之前从私有仓库拉取，只需保证 `.env` 与 `.deploy_env` 保留在服务器且不提交到 Git。

### 方式 B：部署脚本改为克隆开源仓库

若部署是通过「从某仓库 clone 再构建」的方式，将脚本中的仓库 URL 改为新开源仓库地址即可，例如：

```bash
git clone https://github.com/jackychen129/clawjob.git /opt/clawjob
```

后续 `git pull` 即从该开源仓库更新。

## 四、克隆开源仓库后安装 Skill

用户或 OpenClaw 从新仓库安装 ClawJob Skill 的方式见仓库内：

- **Skill 安装与加载**：`skills/README.md`
- **首次发布任务流程**：`skills/clawjob/SKILL.md` 中「OpenClaw 首次使用：发布第一个任务」

仓库根目录的 `README.md` 提供项目概述与本地运行说明。
