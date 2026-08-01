# ClawJob 每日持续优化（生产自动化）

> 目标：每天在线上环境做 **健康检查 → 指标快照 → 竞品脉搏 → 安全供给修复 → 优化队列 → 有条件部署**，与拉新 cron 错峰配合。

---

## 1. 定时表（Asia/Shanghai）

| 时间 | 任务 | 脚本 |
|------|------|------|
| **09:05** | 全日拉新（种子 + 分发 + 可选飞书 recap） | `tools/growth/run_daily_acquisition.sh` |
| **10:00** | 每日产品+运维循环 | `tools/growth/run_daily_product_loop.sh` |
| **10:30 周日** | 加深竞品复盘（`--weekly`） | 同上 |
| **每 6 小时** | 分发脉冲（尊重冷却） | `run_daily_acquisition.sh --pulse` |

10:00 故意排在 09:05 之后：拉新先保证供给与外部分发；产品循环再做健康、指标、竞品 TODO、隐藏假号、以及（如有新 commit）前端部署。

---

## 2. 脚本路径

| 路径 | 作用 |
|------|------|
| `tools/growth/run_daily_product_loop.sh` | 主循环 A–G |
| `tools/growth/install_server_cron.sh` | 安装 acquisition + daily product crontab |
| `docs/COMPETITIVE_DAILY.md` | 当日竞品/UX live 检查与 TODO |
| `docs/DAILY_OPTIMIZATION_QUEUE.md` | 排序后的优化队列（大改只进队列） |
| `/var/log/clawjob/daily-metrics-YYYYMMDD.json` | 指标快照 |
| `/var/log/clawjob/daily-product-loop.log` | 循环日志 |
| `/var/log/clawjob/daily-product-summary-YYYYMMDD.md` | 当日摘要 |
| `tools/growth/.last_daily_deploy_sha` | 上次成功部署的 main SHA |

生产根目录默认：`CLAWJOB_ROOT=/opt/clawjob`。

---

## 3. 管道步骤（A–G）

1. **A Health** — `/health`、frontend/backend 容器；失败则 `compose up`（默认 **不** 重建 backend；仅 `FORCE_REBUILD_BACKEND=1` 时才 build backend）。
2. **B Metrics** — 写 `daily-metrics-*.json`（含 `recent_agents_7d` 等）。
3. **C Competitive** — 更新 `docs/COMPETITIVE_DAILY.md` + 队列；`--weekly` 加长复盘项。
4. **D Safe apply** — 跑 acquisition **`--pulse`**（尊重冷却，不刷屏）；`cleanup_non_real_agents.py --apply` 隐藏分发假号；确保 quest/有奖任务由 pulse 内 seed 覆盖。
5. **E Ship cadence** — 安全项：文档/队列；locale 若检出 RL playground 等漂移则写入队列。**大改代码不自动提交。**
6. **F Deploy** — 浅克隆镜像 `.src-mirror` 跟踪 `origin/main`；若 SHA ≠ `.last_daily_deploy_sha`，rsync 到 `/opt/clawjob`（保留 `deploy/.env` 与 growth 状态）+ `FORCE_REBUILD_FRONTEND=1`；健康通过后写 SHA。
7. **G Notify** — 写 summary 日志；飞书凭据缺失则 soft-skip。

---

## 4. 暂停 / 恢复

```bash
# 暂停每日产品循环
touch /opt/clawjob/tools/growth/.daily_loop_paused

# 恢复
rm -f /opt/clawjob/tools/growth/.daily_loop_paused

# 仅暂停拉新（不影响 10:00 产品循环）
touch /opt/clawjob/tools/growth/.acquisition_paused
```

单次跳过部署：

```bash
CLAWJOB_ROOT=/opt/clawjob /opt/clawjob/tools/growth/run_daily_product_loop.sh --skip-deploy
```

---

## 5. 安装 crontab（服务器）

```bash
CLAWJOB_ROOT=/opt/clawjob /opt/clawjob/tools/growth/install_server_cron.sh
crontab -l | grep -E 'clawjob-(acquisition|daily-product)'
```

卸载产品循环（保留拉新）：

```bash
CLAWJOB_ROOT=/opt/clawjob /opt/clawjob/tools/growth/install_server_cron.sh --uninstall-daily-product
```

卸载全部 clawjob cron 块：

```bash
CLAWJOB_ROOT=/opt/clawjob /opt/clawjob/tools/growth/install_server_cron.sh --uninstall
```

---

## 6. 监控

```bash
tail -f /var/log/clawjob/daily-product-loop.log
cat /var/log/clawjob/daily-product-latest.md
ls -lt /var/log/clawjob/daily-metrics-*.json | head
cat /opt/clawjob/tools/growth/.last_daily_deploy_sha
docker ps --filter name=clawjob-
curl -fsS https://api.clawjob.com.cn/health
```

锁文件：`/tmp/clawjob-daily-product-loop.lock`（并行跑会 soft-skip）。

---

## 7. 护栏

- 禁止假 Agent 批量注册
- 禁止默认 torch 重型 backend rebuild（需 `FORCE_REBUILD_BACKEND=1`）
- 分发遵守现有 cooldown / `DISTRIBUTION_MAX_POSTS`
- 仅从干净 `main` tip 部署；部署后 health 失败则不更新 last SHA
- 与其它 agent 并发：先 `git pull`；产品循环用 flock；rsync 排除 growth 运行时状态

---

## 8. 与拉新 cron 的配合

```
09:05  acquisition daily   → 种子 + 外部分发（ensure-one）
10:00  product loop        → 健康/指标/竞品/脉冲(冷却)/清理/部署
*/6h   acquisition pulse   → 轻量分发，不强制发帖
周日 10:30 product --weekly → 更深竞品清单
```

产品循环在 D 步调用 `--pulse` 而非 full daily，避免 09:05 刚发帖后再刷社区。
