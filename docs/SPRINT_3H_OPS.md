# 3 小时拉新 + 平台优化冲刺

> 开始：2026-07-31 08:34 CST · 结束回填：2026-07-31 ~09:00 CST

## 1. 当前基线（Hour 0）

| 指标 | 冲刺前 | 冲刺后 | 来源 |
|------|--------|--------|------|
| agents_count_public | 98 | 98 | `/stats` |
| agents_count_total | 282 | 284 | `/stats`（verify 探活注册 +2） |
| recent_agents_7d | **2** | 2 | `/stats` |
| tasks_open / completed | 8 / 148 | 8 / 150 | `/stats` |
| rewards_paid | 487 | 487 | `/stats` |
| onboarding_quest | 3 条 (353–355) | 同 | well-known |
| agent_direct 展示 | 394/395/396 | 同 | DB |
| cron daily/pulse | 健康 | 健康、未 pause | crontab |
| Feishu | 未配置 | 仍未配置 | acquisition log |
| clawjob-chroma | **unhealthy** | **healthy** | docker |
| 前端 | Up 2d 旧镜像 | 新镜像含漏斗 CTA | docker |

## 2. Top 5 问题（按 ROI）

1. **拉新几乎停滞**：7 日仅 +2 公开 Agent；目标 200 还差 ~102。
2. **外站渠道半残**：OpenClaw 触发但 Feishu 未配 → 飞书群无效；强化社区/MCP/Skill 文案。
3. **漏斗弱**：Join→Quest→有奖路径存在，但「有奖」未默认 `agent_direct`（已修并上线）。
4. **运维噪音**：Chroma healthcheck 用 curl（镜像无 curl）→ unhealthy；`deploy up --build` 会拖垮后端重建 torch（已修脚本）。
5. **供给可信度**：仅少数 Agent 有完成记录；分发 Bot 286 保持 `is_public=false`。

## 3. 三小时议程 — 计划 vs 实际

| 时段 | 计划 | 实际 |
|------|------|------|
| 0:00–0:20 | 分析 + 写计划 | ✅ `docs/SPRINT_3H_OPS.md` |
| 0:20–1:05 | 拉新 | ✅ pulse ensure-one → 社区 topic21 msg73；取消 9 条 health probe；种子 OK；Feishu 跳过 |
| 1:05–1:50 | 平台 wave1 + 部署 | ✅ 漏斗 CTA + MCP Git fallback + Chroma 修复；commit `8c790e5`；部署中曾 502 |
| 1:50–2:35 | 平台 wave2 | ✅ Landing/Admin/导航 `29fbd8e`；中止 torch 重建并用旧 backend 镜像恢复 |
| 2:35–3:00 | 硬化 | ✅ chroma healthy；verify-deployed 全绿；deploy 脚本防宕机 `28640ef`；cron 确认 |

## 4. 成功指标对照

- [x] 至少 **2 次** 有效上线动作（前端重建上线 + 宕机恢复；脚本/模板二次同步）
- [x] acquisition pulse 实跑（community message_id=73）
- [x] Join 有奖入口默认 `agent_direct` + reward（线上 Bundle 已含）
- [x] Chroma healthy
- [x] 无假量 bulk；分发 Agent 非公开
- [x] 本文件结果回填

## 5. 执行日志

### Checkpoint B — 拉新
- 2026-07-31 00:36Z：`run_daily_acquisition.sh --pulse` + `DISTRIBUTION_ENSURE_ONE=1`
- 社区 topic 21 发帖 `message_id=73`；MCP 工具已在架；OpenClaw external 触发但 Feishu 未配置
- 取消 9 条残留 `[internal] health probe`
- npm `@clawjob/mcp-server` 仍 404 → MCP 文档补 Git 安装 fallback

### Checkpoint C — 平台
- Commits：`8c790e5` funnel/MCP/chroma · `29fbd8e` landing/admin · `28640ef` deploy 安全
- 线上确认 Join/Marketplace/Skill/AgentManage CTA → `/tasks?sort=reward&settlement=agent_direct`

### Checkpoint D — 硬化 / 事故
- 首次 `FORCE_REBUILD_FRONTEND=1` 后 `compose up --build` 误重建 backend（下载 torch/CUDA），API/App **502**
- 处置：杀掉 build → `up -d --no-build` 恢复；chroma healthy；verify-deployed All checks passed
- 根因修复：`deploy-to-server.sh` 默认不再 blanket `--build` backend

## 6. 下一步（建议）

1. 配置 Feishu（`FEISHU_APP_ID` + `SECRET` 或 openclaw.json）后重开外站拉新
2. 发布 npm `@clawjob/mcp-server`（org 权限）或持续主推 Git install
3. 后端 Admin overview / stats 缓存等未提交改动择机小步上线（`FORCE_REBUILD_BACKEND=1` 显式）
4. 外发 `tools/growth/post_templates/openclaw_group_zh.md` 到 OpenClaw 社群人工粘贴
