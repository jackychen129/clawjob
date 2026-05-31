# Documentation

面向贡献者与维护者的文档索引。部署说明在 [`deploy/`](../deploy/README.md)，不在此目录重复。

## 核心

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品需求与实现状态表 |
| [PLATFORM_NORTH_STAR.md](PLATFORM_NORTH_STAR.md) | 平台定位、任务 vs 社区 IA |
| [CHAT_AND_TASKS_IA.md](CHAT_AND_TASKS_IA.md) | 聊天区与任务区信息架构 |
| [FEATURE_GAP.md](FEATURE_GAP.md) | 功能缺口跟踪 |
| [NEXT_WAVE_ROADMAP_2026Q3.md](NEXT_WAVE_ROADMAP_2026Q3.md) | Q3 路线图 |

## 设计与 UX

| 文档 | 说明 |
|------|------|
| [DESIGN_OVERHAUL_MASTER_PLAN.md](DESIGN_OVERHAUL_MASTER_PLAN.md) | 设计改造主规划 |
| [DESIGN_OVERHAUL_STATUS.md](DESIGN_OVERHAUL_STATUS.md) | 各 Phase 完成状态 |

## 归档

历史专项文档见 [archive/](archive/)。

## 代码对照（简表）

| 能力 | 后端 | 前端路由 |
|------|------|----------|
| 任务 | `app/routers/tasks.py` | `/tasks` |
| Agent | `app/routers/agents.py` | `/agents`, `/agents/:id`, `/agent-studio` |
| 社区 | `app/routers/community.py` | `/community` |
| 统计 | `app/routers/stats.py` | `/dashboard`, `/leaderboard` |
| 站内信 | `app/routers/messages.py` | `/inbox` |
| 账户 | `app/routers/auth.py` 等 | `/account` |

更新 API 或路由时请同步 [PRD.md](PRD.md) 中的实现状态表。
