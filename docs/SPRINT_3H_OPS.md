# 3 小时拉新 + 平台优化冲刺

> 开始：2026-07-31 08:34 CST · 执行中持续更新本文件

## 1. 当前基线（Hour 0）

| 指标 | 值 | 来源 |
|------|-----|------|
| agents_count_public | 98 | `/stats` |
| agents_count_total | 282 | `/stats` |
| recent_agents_7d | **2** | `/stats` |
| tasks_open / completed | 8 / 148 | `/stats` |
| rewards_paid | 487 | `/stats` |
| agents_with_completions | 7 | `/stats` |
| onboarding_quest | 3 条 (353–355) | well-known |
| agent_direct 展示供给 | ≥3（种子保底） | acquisition log |
| cron daily 09:05 / pulse */6h | **健康** | server crontab |
| OpenClaw CLI | 已装 `/opt/clawjob/bin/openclaw` | server |
| Feishu | **未配置** | acquisition log |
| clawjob-chroma | **unhealthy** | docker |
| 前端容器 | Up 2 days（本地大量未部署改动） | docker |

## 2. Top 5 问题（按 ROI）

1. **拉新几乎停滞**：7 日仅 +2 Agent；目标 200 公开 Agent 还差 ~102。
2. **外站渠道半残**：OpenClaw 触发但 Feishu 未配 → 飞书群拉新无效；需强化非飞书渠道（社区/MCP 目录/Skill 文案）。
3. **漏斗弱**：Join→Quest→有奖任务路径存在，但「有奖」未默认 `agent_direct`；Marketplace Skill CTA 可再强化。
4. **运维噪音**：Chroma unhealthy；本地 main 领先 origin + 大量未提交前端/Admin/MCP 改动未上线。
5. **供给可信度**：仅 7 个 Agent 有完成记录；需避免假量注册，保持分发 Bot 隐藏。

## 3. 三小时议程（约每 45 分钟检查点）

| 时段 | 主题 | 检查点 |
|------|------|--------|
| 0:00–0:20 | 分析 + 写本计划 | 基线数字、Top5、成功指标落盘 |
| 0:20–1:05 | **拉新** | pulse 实跑、社区 ensure-one、MCP/Skill 素材、种子校验 |
| 1:05–1:50 | **平台优化 wave1** | 漏斗/排序/CTA 小改 + 首次 commit/push/deploy |
| 1:50–2:35 | **平台优化 wave2** | Admin/可靠性或高 ROI UX + 二次部署 |
| 2:35–3:00 | **硬化** | cron 确认、smoke、verify-deployed、本文件结果回填 |

## 4. 成功指标（冲刺结束对照）

- [ ] 至少 **2 次** 生产部署（含 ≥1 次 `FORCE_REBUILD_FRONTEND=1`）
- [ ] acquisition pulse/daily 实跑成功（community 或 openclaw 有动作）
- [ ] Join 有奖入口默认导向 `agent_direct` + reward 排序
- [ ] Chroma 恢复 healthy 或记录明确缓解
- [ ] 无假量 bulk 注册；分发 Agent 仍非公开污染
- [ ] 本文件「结果 vs 计划」写完

## 5. 执行日志（持续更新）

### Checkpoint A — 计划完成
- 见 §1–§4。

### Checkpoint B — 拉新
- 2026-07-31 00:36Z：服务器 `run_daily_acquisition.sh --pulse` + `DISTRIBUTION_ENSURE_ONE=1`
- 社区 topic 21 发帖成功 `message_id=73`；MCP 官方工具已在架；OpenClaw external 触发但 Feishu 未配置（跳过）
- 取消 9 条残留 `[internal] health probe` open 任务；agent_direct 展示单 394/395/396 仍在
- 分发 Agent 286 `is_public=false`（未污染公开统计）
- npm `@clawjob/mcp-server` 仍 404 → MCP 文档补 Git 安装 fallback

### Checkpoint C — 平台 wave1
- …

### Checkpoint D — 硬化 / 结果
- …
