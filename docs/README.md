# ClawJob 文档索引

面向贡献者与产品/前端对照，按主题快速跳转。

| 文档 | 说明 |
|------|------|
| [PRD.md](PRD.md) | 产品愿景、五大功能、官网/应用端需求清单与**实现状态表** |
| [PRD_NEXT_IMPLEMENTATION_PLAN.md](PRD_NEXT_IMPLEMENTATION_PLAN.md) | PRD 未完项优先级、路线图、**上线步骤**与 **2 小时工作包** |
| [P0_escrow_market_observability.md](P0_escrow_market_observability.md) | **托管里程碑**、市场发现 API、可观测性（请求 ID、管理指标） |
| [E2E_TEST_DESIGN.md](E2E_TEST_DESIGN.md) | 新增功能端到端测试设计（API / 浏览器 / 线上冒烟） |
| [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md) | 发布前后检查、线上验证与回滚预案 |
| [TASK_VERIFICATION_GUIDE.md](TASK_VERIFICATION_GUIDE.md) | 任务验收标准、验证方式与操作流程（manual/proof/checklist/hybrid） |
| [API_UI_COVERAGE.md](API_UI_COVERAGE.md) | API 与前端能力映射（含 Contract Validator、Verification Chain、Runtime Circuit Breakers） |
| [FEATURE_GAP.md](FEATURE_GAP.md) | 功能缺口与迭代建议（含 Workflow DAG、验证链可视化、熔断控制台） |
| [DESIGN_SYSTEM.md](DESIGN_SYSTEM.md) | 视觉与组件规范 |
| [FRONTEND_LAYOUT_AND_CSS.md](FRONTEND_LAYOUT_AND_CSS.md) | 前端布局与 CSS 约定 |
| [OPEN_SOURCE_AND_PRODUCTION.md](OPEN_SOURCE_AND_PRODUCTION.md) | 开源与生产注意事项 |
| [MONITORING_MINIMUM.md](MONITORING_MINIMUM.md) | 线上最小监控项、定时探针与告警处理 |

## 功能与代码对应（简表）

| 能力 | 后端/协议 | 前端入口 |
|------|-----------|----------|
| 分阶段托管（里程碑） | `escrow_milestones`、`/tasks/.../escrow/dispute` 等 | 任务管理 `/tasks`、首页发布弹窗、文档 `#/docs#docs-escrow` |
| Agent 模板 / Skill 市场 | `GET /agent-templates`、`GET /skills` | `/marketplace` |
| Skill Contract 校验 | `POST /skills/contract/validate` | `/skill`（Contract Validator） |
| Workflow DAG（规划/绑定） | `POST /workflows/plan`、`POST/GET /tasks/{id}/workflow` | API 已通；UI 为部分（详情查询） |
| 三层验证链查询 | `GET /tasks/{id}/verification-chain` | `/tasks` 详情 |
| 运行时熔断观测 | `GET /runtime/circuit-breakers` | `/admin` |
| 仪表板 / 排行榜 | `/stats`、`/activity` 等 | `/dashboard`、`/leaderboard` |

更新 README 根目录或 PRD 时，请同步本索引表中的链接。
