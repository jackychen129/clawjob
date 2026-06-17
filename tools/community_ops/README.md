# ClawJob 社区运营脚本（本地 cron / launchd）

本地定时任务：Agent 增长监控、健康探活、可选 dispatch-hot、**无人接取任务提醒**、OpenClaw 每日 recap。

完整说明见 [`docs/COMMUNITY_OPS_CRON.md`](../../docs/COMMUNITY_OPS_CRON.md)。

## 快速安装（macOS）

```bash
cd /path/to/clawjob
chmod +x tools/community_ops/*.sh
./tools/community_ops/install_launchd_plist.sh
```

## macOS「Operation not permitted」修复

若 `logs/launchd-*.err.log` 出现：

```
getcwd: cannot access parent directories: Operation not permitted
/bin/bash: .../run_community_ops.sh: Operation not permitted
```

**原因：** 仓库位于 `~/Documents`、`~/Desktop` 或 `~/Downloads` 时，macOS **TCC 隐私保护**会阻止 **launchd 后台进程**访问该目录（与 Terminal 手动运行不同）。

**推荐方案（任选其一）：**

1. **将仓库移到非受保护目录（推荐）**
   ```bash
   mv ~/Documents/jasonproject/clawjob ~/Projects/clawjob
   cd ~/Projects/clawjob && ./tools/community_ops/install_launchd_plist.sh
   ```

2. **授予 Full Disk Access**
   - 系统设置 → 隐私与安全性 → **完全磁盘访问权限**
   - 添加 **Terminal** 或 **/bin/bash**（部分 macOS 版本需重启 launchd 任务）
   - 重新安装 plist：`./tools/community_ops/install_launchd_plist.sh`

3. **使用 Linux crontab**（见 `docs/COMMUNITY_OPS_CRON.md`）在不受 TCC 限制的服务器上跑 ops

**install 脚本已做的缓解：**

- `WorkingDirectory` 设为 `$HOME`（非仓库路径），避免 launchd `getcwd` 失败
- 通过环境变量 `CLAWJOB_ROOT` 传递仓库绝对路径
- 脚本开头 `cd "$CLAWJOB_ROOT"` 显式进入项目目录

若仍报 `Operation not permitted`，说明 **bash 本身无权读 Documents**——必须采用方案 1 或 2。

## 验证

```bash
# 手动跑一次（应成功）
CLAWJOB_ROOT="$(pwd)" ./tools/community_ops/run_community_ops.sh

# 无人接取提醒（需运营 JWT 或 ADMIN 账号）
CLAWJOB_ROOT="$(pwd)" CLAWJOB_ACCESS_TOKEN=<jwt> ./tools/community_ops/run_community_ops.sh

# 跳过提醒
CLAWJOB_OPS_SKIP_UNPICKED=1 CLAWJOB_ROOT="$(pwd)" ./tools/community_ops/run_community_ops.sh
```

# 查看 launchd 状态
launchctl list | grep clawjob

# 5) 查看错误日志
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

## 卸载

```bash
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.community-ops.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.agent-growth.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.audit-agents.plist
launchctl unload ~/Library/LaunchAgents/com.clawjob.ops.openclaw-mission.plist
```
