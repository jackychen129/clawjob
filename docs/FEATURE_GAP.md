# 功能缺口总览（PRD / 页面 / 仅 API）

> 便于产品与研发对齐：**已实现** 指主站 `app` 内有等价操作或已用其它方式落地；**未实现** 指仍缺页面、缺闭环或仅后端/MCP 可用。  
> 更新时间随仓库迭代，若与 `docs/PRD.md`、`docs/API_UI_COVERAGE.md` 冲突，以代码与 API 为准。

---

## 一、PRD 中仍标「部分 / 占位 / 待实现」的能力

| 能力 | PRD 位置 | 说明 | 当前状态 |
|------|----------|------|----------|
| 技能进化树与 XP（完整图谱、折旧） | 五大功能 #1 | 账户页有技能树汇总；任务侧有技能进度；**动态图谱、技能折旧** 未做 | 部分 |
| Dashboard 资产 ROI「完整 K 线」 | 五大功能 #2 / PRD 表 | 有益收曲线 `/stats/roi-series`；**交易所级 K 线** 未承诺完成 | 部分 |
| Agent 实验室（Dark / CoT / 状态机） | 应用端 #7 | 无独立页面 | 未实现 |
| 自动重试（Agent 执行侧） | 应用端 #10 | **完成回调 Webhook**：重试有，`output_data.webhook_delivery` + 任务详情展示；**POST /execute** 的 `retry_count` 见账户页说明；Agent 执行侧重试仍偏 API | 部分 |
| 训练沙箱 | 应用端 #1 | 明确 **Out of scope** | 不做 |
| 协作编排 Swarm（PRD 原文「规划中」） | 五大功能 #5 | 已用 **Escrow 三里程碑 + Marketplace 向导** 做 Beta 落地，非独立 Swarm 服务 | **Beta（已替代占位）** |
| 技能包有偿分享 / 商业化 | 五大功能 · 技能包导出 | 市场下载链接 + Skill 发布；**付费结算链** 未做 | 部分 |
| 平台中转账户 `/platform/clearing-account*` | — | 需 **平台管理员密钥**，非超管 JWT | **仅 API** |
| 官网 10 项中的「合作伙伴背书墙」 | PRD 官网表 | 已写下线 | 已下线 |

---

## 二、有后端 API、主站无完整 UI 或仅调试入口

| API 区域 | 说明 |
|----------|------|
| `POST /memory`、`GET /memory/*` | 账户页开发者工具：**search** + **GET /memory/{id}** + **POST /memory**；长 JSON 可折叠（`<details>`） |
| `GET /tools`、`POST /tools`、`POST /agents/{id}/use-tool` | 账户页 **列出工具**；创建工具/Agent 调工具 **无向导** |
| `GET /a2a/tasks/*`、`POST .../messages` | **任务管理 → 任务详情**：发布方/接取方可见 **A2A 同步卡片**、**协作留言**（与评论同源）；独立「A2A 控制台」仍无 |
| `POST /skills/contract/validate` | Skill 页面已提供 Contract Validator，但仍以 JSON 输入为主；缺表单化模板与历史版本管理 |
| `POST /workflows/plan`、`POST/GET /tasks/{id}/workflow` | 后端 DAG 规划/绑定/可用性判定已落地；任务详情已提供 **只读拓扑**（发布方仍有表单编辑）；**拖拽编排 / 批量节点** 仍为增强项 |
| `GET /tasks/{id}/verification-chain` | 任务详情已 **结构化展示** 声明/预检/交叉；**图形式分层报告与失败归因聚合** 仍可增强 |
| `GET /runtime/circuit-breakers` | 管理后台可查看熔断状态，并支持 **open / reset / half_open / close**；**告警策略配置** 仍为增强项 |
| `GET /platform/clearing-account`、`PATCH`、`/records` | **无 UI**（密钥鉴权） |
| Legacy `POST /agents`（agent_manager）等与主业务并行 | 集成/实验向，**非任务大厅主路径** |

---

## 三、主站已打通的闭环（易与「未实现」混淆）

| 流程 | 位置 |
|------|------|
| Skill 绑定 token → 发布到 Skill 市场 → 预填官方 ZIP → 上架状态/撤下 | **Agent 管理** + **Marketplace**；`/agents/mine` 含 `published_skill_id` |
| Agent 模板发布 / 撤下 | Agent 管理、Marketplace |
| Swarm（Beta） | Marketplace 向导 → 任务发布预填 Escrow |
| 候选人列表 | `/candidates` |
| 管理后台指标 / 日志 / 争议 | `/admin`（超管） |
| 运行时熔断状态观测 | `/admin`（超管） |
| Skill Contract 预校验 | `/skill`（Contract Validator） |
| 验证链查询（声明/沙盒/交叉） | `/tasks` 详情 |

---

## 四、建议迭代顺序（非承诺）

1. PRD 表与本文同步（尤其 Swarm、Escrow 证据链）。  
2. Workflow DAG：补图形化编排器（节点模板、依赖拖拽、拓扑错误提示）。  
3. Verification Chain：补结构化报告卡片（非 JSON 原文）与失败原因聚类。  
4. Runtime Circuit Breaker：补管理操作（reset/open/half-open）与告警阈值配置。  
5. ~~Memory / Tools：收敛为「开发者设置」单区~~ → **账户页已分区（工具 / 记忆）并支持按 ID 取记忆**；创建工具 / Agent 调工具向导仍为增强项。  
6. Clearing 账户：独立 **平台运营** 工具或 CLI，避免与普通超管混淆。  
7. ~~A2A：任务详情内嵌「协作消息」~~ → **已内嵌**（发布/接取身份）；可再迭代独立控制台与推送。

---

*若你补充优先级，可把对应行改成 Issue 编号并链回本文件。*
