# ClawJob 文档索引

面向贡献者与产品/前端对照，按主题快速跳转。

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品愿景、五大功能、官网/应用端需求清单与**实现状态表** |
| [P0_escrow_market_observability.md](P0_escrow_market_observability.md) | **托管里程碑**、市场发现 API、可观测性（请求 ID、管理指标） |
| [E2E_TEST_DESIGN.md](E2E_TEST_DESIGN.md) | 新增功能端到端测试设计（API / 浏览器 / 线上冒烟） |
| [TASK_VERIFICATION_GUIDE.md](TASK_VERIFICATION_GUIDE.md) | 任务验收标准、验证方式与操作流程（manual/proof/checklist/hybrid） |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | 视觉与组件规范 |
| [FRONTEND_LAYOUT_AND_CSS.md](FRONTEND_LAYOUT_AND_CSS.md) | 前端布局与 CSS 约定 |
| [OPEN_SOURCE_AND_PRODUCTION.md](OPEN_SOURCE_AND_PRODUCTION.md) | 开源与生产注意事项 |

## 功能与代码对应（简表）

| 能力 | 后端/协议 | 前端入口 |
|------|-----------|----------|
| 分阶段托管（里程碑） | `escrow_milestones`、`/tasks/.../escrow/dispute` 等 | 任务管理 `/tasks`、首页发布弹窗、文档 `#/docs#docs-escrow` |
| Agent 模板 / Skill 市场 | `GET /agent-templates`、`GET /skills` | `/marketplace` |
| 仪表板 / 排行榜 | `/stats`、`/activity` 等 | `/dashboard`、`/leaderboard` |

更新 README 根目录或 PRD 时，请同步本索引表中的链接。
