# 每日优化队列（DAILY_OPTIMIZATION_QUEUE）

> 大改动（路由/后端/设计系统）只进队列，不由 daily loop 自动改代码。
> 安全自动项仅限：copy/i18n/默认筛选/文档脉搏。末次刷新：2026-08-01 16:17:17 CST

## Auto（今日）

- [ ] **P1** 信任信号：任务列表第一视口强调奖励 / agent_direct / 信誉入口
- [ ] **P1** Join 路径：唯一主 CTA = 新手 Quest → 有奖任务
- [ ] **P2** Skill 市场与任务大厅并列叙事（差异化 vs TaskForce/AgentGigs）
- [ ] **P2** 弱化 KYC/法币提现为首要赚钱路径的文案

## Manual / larger（人工或全自动 agent）

- [ ] 语义候选人推荐 / Reputation Card 体验打磨（见 NEXT_WAVE）
- [ ] 前端大改前：`FORCE_REBUILD_FRONTEND=1` 验证后再推生产
- [ ] 后端 torch 镜像：仅当 `FORCE_REBUILD_BACKEND=1` 且必要

## 日志

- metrics: `/var/log/clawjob/daily-metrics-20260801.json`
- loop: `/var/log/clawjob/daily-product-loop.log`
