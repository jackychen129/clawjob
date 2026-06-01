# 功能缺口总览（PRD / 页面 / 仅 API）

> 便于产品与研发对齐：**已实现** 指主站 `app` 内有等价操作或已用其它方式落地；**未实现** 指仍缺页面、缺闭环或仅后端/MCP 可用。  
> 更新时间随仓库迭代，若与 `docs/PRD.md`、`docs/API_UI_COVERAGE.md` 冲突，以代码与 API 为准。

---

## 一、PRD 中仍标「部分 / 占位 / 待实现」的能力

| 能力 | PRD 位置 | 说明 | 当前状态 |
|------|----------|------|----------|
| 技能进化树与 XP（完整图谱、折旧） | 五大功能 #1 | 账户/Dashboard 有条形技能汇总 + 折旧策略展示；**全图谱可视化** 仍为增强项 | 部分 |
| Dashboard 资产 ROI「完整 K 线」 | 五大功能 #2 / PRD 表 | `/stats/roi-series` + 交互 tooltip/节点标注；**交易所级 K 线** 未承诺完成 | 部分 |
| Agent 实验室 / A2A 控制台 | 应用端 #7 | `/a2a` 协作收件箱 + 任务详情内嵌 A2A；`/agent-lab`、`/a2a-console` 仍重定向 `/agents` | 部分 |
| 自动重试（Agent 执行侧） | 应用端 #10 | 任务详情「可观测性」展示 `webhook_delivery` 与 `last_execute`；账户页有 execute API 说明 | 部分 |
| 训练沙箱 | 应用端 #1 | 明确 **Out of scope** | 不做 |
| 协作编排 Swarm（PRD 原文「规划中」） | 五大功能 #5 | 已用 **Escrow 三里程碑 + Marketplace 向导** 做 Beta 落地，非独立 Swarm 服务 | **Beta（已替代占位）** |
| 技能包有偿分享 / 商业化 | 五大功能 · 技能包导出 | **付费结算链已端到端闭环（D-19）**：作者在 Marketplace 定价（按下载/按调用/订阅）→ 买家购买/订阅获得权益（幂等）或 per_invoke 随任务结算 → 作者分成入可提现佣金余额、平台抽成入中转账户 → 账户页查看收入与购买、退款窗口内可退款。路由不再受 `CLAWJOB_ENTERPRISE` 门控。**税务发票 / 第三方支付网关充值** 仍为 Phase 2 | **已闭环（税票为 Phase 2）** |
| 平台中转账户 `/platform/clearing-account*` | — | 需 **平台管理员密钥**，非超管 JWT | **仅 API** |
| 官网 10 项中的「合作伙伴背书墙」 | PRD 官网表 | 已写下线 | 已下线 |

---

## 二、有后端 API、主站无完整 UI 或仅调试入口

| API 区域 | 说明 |
|----------|------|
| `GET /account/insights` | ✅ **已接入 DashboardView**：发布方报表卡片（净支出/完成率/分类分布）；仅登录可见 |
| `POST /memory`、`GET /memory/*` | 账户页开发者工具：**search** + **GET /memory/{id}** + **POST /memory**；长 JSON 可折叠（`<details>`） |
| `GET /tools`、`POST /tools`、`POST /agents/{id}/use-tool` | 账户页 **工具列表 + Agent use-tool 向导**（选 Agent/工具、参数 JSON、历史回填） | — |
| `GET /a2a/tasks/*`、`POST .../messages` | **任务管理 → 任务详情**：发布方/接取方可见 **A2A 同步卡片**、**协作留言**（与评论同源）；独立「A2A 控制台」仍无 |
| `POST /skills/contract/validate` | Skill 页面已提供 Contract Validator，但仍以 JSON 输入为主；缺表单化模板与历史版本管理 |
| `POST /workflows/plan`、`POST/GET /tasks/{id}/workflow` | 任务详情 **SVG 只读拓扑** + 发布方节点/边编辑与绑定 | **拖拽编排** 仍为增强项 |
| `GET /tasks/{id}/verification-chain` | 结构化卡片 + **失败原因聚类**；原始 JSON 折叠 | 图形式分层报告仍可增强 |
| `GET /runtime/circuit-breakers` | 管理后台熔断控制 + **`PATCH /runtime/circuit-breakers/config`** 阈值配置 | — |
| `GET /platform/clearing-account`、`PATCH`、`/records` | **`#/ops`** 运营 UI（平台密钥）+ 超管 `/admin` 内嵌 |
| `GET /account/kyc/*`、`POST /admin/kyc/*` | 账户个人/企业 KYC + 沙盒跳过；管理员审核与 **CSV 导出** | — |
| Legacy `POST /agents`（agent_manager）等与主业务并行 | 集成/实验向，**非任务大厅主路径** |

---

## 三、主站已打通的闭环（易与「未实现」混淆）

| 流程 | 位置 |
|------|------|
| Skill 绑定 token → 发布到 Skill 市场 → 预填官方 ZIP → 上架状态/撤下 | **Agent 管理** + **Marketplace**；`/agents/mine` 含 `published_skill_id` |
| **Skill 付费结算链（D-19）**：作者定价 → 买家购买/订阅/按调用 → 作者分成 + 平台抽成 → 收入/购买/退款 | **Marketplace**（定价/购买/价格 Badge）+ **账户·开发者**（收入明细、购买记录、退款）；API：`POST /skills/{token}/pricing`、`POST /skills/{token}/purchase`、`GET /skills/{token}/entitlement`、`POST /skills/purchases/{id}/refund`、`GET /account/skill-revenue`、`GET /account/skill-purchases` |
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
