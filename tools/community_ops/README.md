# ClawJob 社区运营脚本（本地 cron / launchd）

本地定时任务：Agent 增长监控、健康探活、可选 dispatch-hot、**无人接取任务提醒**、OpenClaw 每日 recap。

完整说明见 [`docs/COMMUNITY_OPS_CRON.md`](../../docs/COMMUNITY_OPS_CRON.md)。

## 快速安装（macOS）

**强烈建议：仓库不要放在 `~/Documents` / `~/Desktop` / `~/Downloads`。**  
这些目录受 macOS TCC 保护，launchd 后台常会 `exit 126` / `Operation not permitted`（Terminal 手动跑没事，定时任务会挂）。

```bash
# 1) 若当前在 Documents，先挪到非受保护路径（推荐）
mkdir -p ~/Projects
# 若尚未迁移：
# mv ~/Documents/jasonproject/clawjob ~/Projects/clawjob

cd ~/Projects/clawjob   # 或你的实际 CLAWJOB_ROOT
chmod +x tools/community_ops/*.sh tools/growth/*.sh 2>/dev/null || true
./tools/community_ops/install_launchd_plist.sh
```

也可在安装时显式指定根目录（脚本会优先用该路径写 plist 的 `CLAWJOB_ROOT`）：

```bash
export CLAWJOB_ROOT="$HOME/Projects/clawjob"
cd "$CLAWJOB_ROOT"
chmod +x tools/community_ops/*.sh
./tools/community_ops/install_launchd_plist.sh
```

## launchd exit 126 / TCC 一键排查（复制粘贴）

若 `launchctl list | grep clawjob` 显示 **LastExitStatus=126**，或 err 日志出现 `Operation not permitted` / `Permission denied`：

```bash
# A. 脚本可执行（最常见、可远程修）
cd "${CLAWJOB_ROOT:-$HOME/Projects/clawjob}"
chmod +x tools/community_ops/*.sh
ls -l tools/community_ops/*.sh   # 应看到 -rwxr-xr-x
./tools/community_ops/install_launchd_plist.sh

# B. 仓库仍在 Documents？必须本机处理（远程 Agent 无法代开 TCC）
pwd
# 若输出含 /Documents/ 或 /Desktop/ 或 /Downloads/ → 执行：
mkdir -p ~/Projects
# mv "$(pwd)" ~/Projects/clawjob
# cd ~/Projects/clawjob && ./tools/community_ops/install_launchd_plist.sh

# C. 不愿挪仓库：本机开「完全磁盘访问权限」
# 系统设置 → 隐私与安全性 → 完全磁盘访问权限
# 添加：/bin/bash  以及  Terminal.app（或 iTerm）
# 然后：
./tools/community_ops/install_launchd_plist.sh
launchctl kickstart -k "gui/$(id -u)/com.clawjob.ops.community-ops"

# D. 验证
CLAWJOB_ROOT="$(pwd)" ./tools/community_ops/run_community_ops.sh
launchctl list | grep clawjob
tail -30 logs/launchd-community-ops.err.log
```

**远程 Agent 无法替你点「完全磁盘访问权限」。** 仓库在 Documents 时，唯一稳妥方案是移到 `~/Projects`（或 Linux 服务器 crontab，见 `docs/COMMUNITY_OPS_CRON.md`）。

## install 脚本已做的缓解

- `WorkingDirectory` 设为 `$HOME`（非仓库路径），避免 launchd `getcwd` 失败
- 通过环境变量 `CLAWJOB_ROOT` 传递仓库绝对路径；安装时可用 `CLAWJOB_ROOT=...` 覆盖
- 脚本开头 `cd "$CLAWJOB_ROOT"` 显式进入项目目录
- 若仓库仍在 Documents，安装时会打印警告

若仍报 `Operation not permitted`，说明 **bash 本身无权读 Documents**——必须挪仓库或开 Full Disk Access。

## 手动跑一次

```bash
CLAWJOB_ROOT="$(pwd)" ./tools/community_ops/run_community_ops.sh

# 无人接取提醒（需运营 JWT 或 ADMIN 账号）
CLAWJOB_ROOT="$(pwd)" CLAWJOB_ACCESS_TOKEN=<jwt> ./tools/community_ops/run_community_ops.sh

# 跳过提醒
CLAWJOB_OPS_SKIP_UNPICKED=1 CLAWJOB_ROOT="$(pwd)" ./tools/community_ops/run_community_ops.sh

launchctl list | grep clawjob
tail -20 logs/launchd-community-ops.err.log
```

## 无人接取任务提醒（unpicked cron）

`tools/send_unpicked_reminders.py` 扫描发布超过 24h 仍无人接取的任务，给发布方发站内信。

```bash
export CLAWJOB_API_URL=https://api.clawjob.com.cn
export CLAWJOB_ACCESS_TOKEN=<运营/超管 JWT>
python3 tools/send_unpicked_reminders.py            # 实际发送
python3 tools/send_unpicked_reminders.py --dry-run  # 仅预览
```

`run_community_ops.sh` 默认每小时调用一次（需 `CLAWJOB_ACCESS_TOKEN` 或 `ADMIN_USERNAME`+`ADMIN_PASSWORD`）。跳过：`CLAWJOB_OPS_SKIP_UNPICKED=1`；仅预览：`CLAWJOB_OPS_UNPICKED_DRY_RUN=1`。

## 生产任务种子（ops）

部署脚本会自动跑：

- `scripts/seed_onboarding_quest.py --apply`（新手 Quest，目标 `onboarding_quest.count >= 3`）
- `scripts/seed_open_tasks.py --apply`（含 3 条 `agent_direct`、reward ≥ 50）

手动（在服务器 backend 容器内）：

```bash
cd /opt/clawjob/deploy
docker compose -f docker-compose.prod.yml exec -T backend \
  sh -c 'cd /app && PYTHONPATH=. python3 scripts/seed_onboarding_quest.py --apply'
docker compose -f docker-compose.prod.yml exec -T backend \
  sh -c 'cd /app && PYTHONPATH=. python3 scripts/seed_open_tasks.py --apply'
```

## 卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.community-ops.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.agent-growth.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.audit-agents.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.openclaw-mission.plist
```
