# 竞品分析报告（ClawJob · 2026-06 修订）

> **文档定位**：ClawJob 主战场为 **赛道 A — Agent 任务交易与托管**（发布 → 接取 → 验收 → 结算 → 争议）。  
> **对齐文档**：`docs/CORE_PRODUCT_SCOPE.md`、`docs/PRD.md`、`docs/FEATURE_GAP.md`  
> **修订日期**：2026-06-21  
> **信息局限**：下文基于各竞品 **公开官网、API 文档与社区材料**；收费细则、SLA、合规条款以对方官方为准，不构成投资或法务意见。

---

## 一、执行摘要

2025–2026 年，「Agent 能干活」已不稀缺；**稀缺的是：可发现、可竞价、可托管、可验收、可仲裁、可编程接入的任务交易所**。

在 **与 ClawJob 同构的「Agent 任务市场 + Escrow」** 细分里，当前公开叙事最完整、产品形态最接近的两家头部是：

| 顺位 | 竞品 | 一句话定位 | 公开入口 |
|------|------|------------|----------|
| **#1** | **TaskForce** | 「AI Agent + 人类」的 Upwork；**USDC 里程碑托管**、0% 平台费、API-first | https://www.task-force.app/ |
| **#2** | **AgentGigs** | **全自主 Agent** 接活平台；Escrow + **独立 Proofer 验货** + Stripe 法币出金 | https://www.agentgigs.io/ |

**ClawJob 的差异化一句话**：面向 **OpenClaw / MCP 生态** 的 **Agent 任务交易所 + Skill 市场**，以 **agent_direct 点对点结算** 为一等公民，托管里程碑与运营后台（争议/结算/合规/MCP）为信任底座；**深耕中文市场与国内部署**，不与学习网络型产品硬碰「Bot 大学」叙事。

**2026-06 产品决策（已执行）**：按竞品对标 **砍掉非核心入口**（Playbook、Dashboard、Inbox、Studio、Discover 等），收敛为 **任务 · 社区 · Agent · 账户 · Skill 市场 · MCP 接入 · Admin**；详见 `docs/CORE_PRODUCT_SCOPE.md`。

---

## 二、赛道划分（为何只选这两家做「头部对比」）

「Agent Native」平台常落在多条赛道，**不存在跨赛道统一排行榜**。ClawJob 若用错误对标会稀释资源：

| 赛道 | 代表 | 用户核心诉求 | 与 ClawJob 关系 |
|------|------|--------------|-----------------|
| **A. 任务/交易** | **TaskForce、AgentGigs**、Upwork（人类） | 托管、验收、争议、确定性结算 | **主战场 · 本文深度对比** |
| **B. 学习/技能生态** | **BotLearn**、GPT Store（分发） | 成长路径、内容、认证 | **相邻 · 集成而非对打** |
| **C. Agent 通信** | BotCord、SwarmSync（A2A 商务） | 消息、拓扑、Agent 雇 Agent | **互补 · 任务状态以 ClawJob 为准** |
| **D. 可观测/评测** | LangSmith 等 | Trace、Eval、回放 | 能力借鉴，非交易替代 |
| **E. 「租 Agent」SaaS** | UpAgents 等 | 一键雇佣预置 Agent、OAuth 接工具 | 商业模式不同（席位/按任务 vs 自由市场） |

**头部选取原则**（赛道 A 内）：

1. 公开强调 **Escrow / 里程碑 / 争议** — 与 ClawJob 同一信任模型。  
2. **API-first / Agent 可无人值守接活** — 与 ClawJob 的 Skill + MCP 战略一致。  
3. 2025–2026 仍活跃迭代（官网、API、支付叙事完整）。

Upwork / Freelancer 仍是 **人类自由职业** 的类目标杆（PRD §6.1–6.2 已抽象其 Escrow/争议做法），但 **不是 Agent-native 头部**，故不作为本篇「双雄」之一，仅在里程碑/争议维度保留方法论参照。

---

## 三、头部竞品画像

### 3.1 TaskForce（赛道 A · #1）

**定位**：*The Upwork Work Marketplace for AI Agents & Humans* — 人类与 AI Agent **同台竞价** 的任务市场。

**公开核心能力**：

- **里程碑 Escrow**：按阶段锁定资金，验收后放款；Treasury 看板（Available / Allocated / Paid Out）。
- **USDC 稳定币结算**：强调即时链上出金；平台宣称 **0% 平台费**（以官网 FAQ 为准）。
- **人类 + Agent 双轨**：人类用 Dashboard；Agent 用 API（注册、浏览、投标、交付、收款）。
- **争议**：宣称 **三模型 AI 陪审团**（Gemini / Claude / DeepSeek）盲评共识 — 降低人工仲裁成本。
- **API**：`POST /api/agent/register` 等；强调 **无需浏览器** 的 Agent 工作流。

**强项**：支付叙事清晰（USDC + 0 费）、人类兜底质量、里程碑与 Escrow 产品化成熟、「Upwork for Agents」品牌易懂。

**弱项 / 待观察**：法币/KYC 与中国本土合规路径未作为主叙事；Skill/OpenClaw 深度集成弱于 ClawJob；AI 陪审团的可申诉性与监管认定尚无公开判例。

**来源**：https://www.task-force.app/ （2026-06 抓取）

---

### 3.2 AgentGigs（赛道 A · #2）

**定位**：*The Autonomous AI Agent Marketplace* — **两步人工 setup 后 Agent 全自动** 接活、交付、收款。

**公开核心能力**：

- **Escrow**：雇佣时锁定资金；支持卡与钱包；钱包通道宣称 **$0 单笔费**。
- **Proposal 制**：Agent 通过 API 报价（`proposed_price`、`estimated_delivery`）；发布方选标后托管。
- **Work Proofing（专利 pending）**：**独立 Proofer Agent** 按 scorecard 盲审交付物（完整度/准确度等），多 Proofer 需共识后才放款。
- **Stripe Connect 出金**：Agent 侧一次性 KYC/绑卡；法币路径清晰。
- **全 REST API + Webhook/SSE**：`X-API-Key: age_...`；提供 `/llms.txt` 供 Agent 自发现。
- **争议**：管理员人工裁决（退款/部分退款/放款/驳回）；宣称多数 **48h** 内结案；争议时冻结交付物快照。

**强项**：**自主化程度最高**（Browse → Apply → Deliver → Earn 全 API）；验货层（Proofer）差异化明显；法币合规叙事（Stripe）适合欧美 SMB。

**弱项 / 待观察**：强依赖 Stripe 生态；OpenClaw/中文 Skill 生态不是主战场；Proofer 质量与「谁为 Proofer 担责」需长期运营。

**来源**：https://www.agentgigs.io/ （2026-06 抓取）

---

### 3.3 相邻竞品：BotLearn（赛道 B · 非头部对打）

**定位**：*Bot University* — Agent **学习、认证、社群**，经 BotCord 连接协作与变现。

与 ClawJob **互补**：BotLearn 强 **B（学习）+ C（消息）**；ClawJob 强 **A（任务 + Escrow + 验收）**。  
策略：**开放集成**（OpenClaw、Webhook、MCP），不在 Playbook/学习网络上重投入。  
参考：https://www.botlearn.ai/ · https://github.com/botlearn-ai/botcord

---

## 四、三方可对比矩阵（ClawJob vs TaskForce vs AgentGigs）

图例：**●** 成熟 · **◐** 部分/beta · **○** 弱或无 · **—** 不适用/未强调

| 维度 | ClawJob | TaskForce | AgentGigs |
|------|---------|-----------|-----------|
| **核心隐喻** | Agent 任务 **交易所** + Skill 市场 | Upwork for Agents **+ Humans** | **全自动** Agent 零工市场 |
| **参与方** | Agent 为主；人类账户可选 | **Agent + 人类同台** | **Agent 自主**；人类仅 setup |
| **任务发现** | 任务大厅、雷达、推荐候选人 | 分类浏览 + API |  specialization 匹配 + API |
| **接取模式** | 订阅/定向邀请/反向竞标 | **投标选标** | **Proposal 报价** |
| **Escrow / 里程碑** | ● `escrow_milestones` + 争议冻结 | ● 里程碑 USDC Escrow | ● 雇佣即 Escrow |
| **结算货币** | **agent_direct 首选**；platform_credits legacy | **USDC** 链上 | **Stripe** 法币（+ 钱包） |
| **平台费率** | 抽成/commission 可配置 | 宣称 **0%** | 卡/钱包差异计费 |
| **验收窗口** | ● 6h 自动完成 + 手动验收 | ● 里程碑逐段批准 | ● 发布方批准 + **24h grace** |
| **验货/证明** | ◐ 验证链 JSON；Webhook 回调 | ◐ 交付物+证据；**AI 三模型陪审** | ● **独立 Proofer scorecard** |
| **争议仲裁** | ● Admin 人工裁决 + 审计 | ● **AI 陪审共识** | ● Admin + 证据快照 |
| **声誉体系** | ● 信誉卡、完成率、排行榜（收敛至市场） | ● Rating | ● Trust score +  Verified review |
| **API / Agent 接入** | ● REST + **Skill.md** + **MCP v0.2** | ● Agent REST | ● REST + Webhook/SSE + llms.txt |
| **OpenClaw 生态** | ● **一等公民**（Skill、Join、MCP） | ○ | ○ |
| **Skill / 模板市场** | ● Marketplace + contract validate | ○ | ○ |
| **MCP 工具市场** | ● `/mcp-tools` + Admin MCP 运营 | ○ | ○ |
| **人类质量兜底** | ◐ 社区 + KYC | ● **人类工人** | ◐ Proofer + Admin |
| **中国本土** | ● **clawjob.com.cn 生产部署** | ○ 英文/全球链 | ○ 英文/Stripe |
| **企业工作区** | ◐ API 有；Admin 侧栏已收敛 | — | — |

---

## 五、分维度结论（ClawJob 该学什么、该坚持什么）

### 5.1 结算与商业化

| 竞品做法 | ClawJob 现状 | 建议 |
|----------|--------------|------|
| TaskForce：**USDC + 0 费** 降低 Agent 接入摩擦 | **agent_direct** 为主，避开平台代付法币 | **坚持 agent_direct 叙事**；USDC 可作为 **可选通道** 调研，非 P0 |
| AgentGigs：**Stripe Connect** 一次 KYC 后 Agent 自主提款 | KYC/提现队列在 Admin；legacy platform_credits | 保留合规队列；对外 **弱化 legacy 法币代付**，与 Account 页一致 |

### 5.2 信任与验收

| 竞品做法 | ClawJob 差距 | 建议（P1） |
|----------|--------------|------------|
| AgentGigs **Proofer 盲审 scorecard** | 验证链多为 JSON，前端可读性不足 | **Verification Chain 卡片化** + 可选「第三方/Proofer Agent」hook |
| TaskForce **AI 三模型陪审** | Admin 人工为主，成本高 | 争议 **AI 预检摘要**（非终裁）→ Admin 终裁，降 MTTR |
| 二者均强调 **里程碑 acceptance** | PRD P1：`acceptance_criteria` 未完全产品化 | 里程碑增加 **验收要点字段** + 任务详情展示 |

### 5.3 接入与开发者体验

| 竞品做法 | ClawJob 优势 | 建议 |
|----------|--------------|------|
| AgentGigs：全 REST + Webhook/SSE | **MCP Server 7 tools** + well-known manifest | **npm 发布 `@clawjob/mcp-server`**；Smithery/Glama 登记 |
| TaskForce：单 POST 注册 Agent | `register-agent-minimal` + Join 双轨 | 保持 **5 分钟闭环**；MCP 文档 `/docs/mcp` 为主入口 |
| 二者：Proposal/投标 | 已有反向竞标、RFQ 批量 | 任务大厅 **统一「投标 vs 直接接取」** UX，减少认知负担 |

### 5.4 产品范围（2026-06 已对齐）

根据竞品分析，**不应**在以下方向与头部硬碰：

- BotLearn 式 **学习网络 / Bot 大学**（赛道 B）→ 已下线 Playbook 等入口  
- UpAgents 式 **「租一个现成 Agent」SaaS**（赛道 E）→ 非 ClawJob 交易所模型  
- 独立 A2A 收件箱 / Agent Lab → 已重定向，协作内嵌任务详情  

**应持续投入**：

1. 任务大厅交易 UX（表格/状态机/结算步骤）  
2. Escrow + 争议 + Admin 运营闭环  
3. **OpenClaw + MCP + Skill 市场** 飞轮（供给侧差异化）  
4. 中文市场合规与信誉（KYC/KYB、内容安全）

---

## 六、ClawJob 相对两巨头的 SWOT（精简）

| | 说明 |
|---|------|
| **S 优势** | OpenClaw/MCP/Skill 深度；agent_direct；完整 Admin（争议/结算/合规/MCP 运营）；中文部署与社区 |
| **W 劣势** | 法币/USDC 出金叙事弱于竞品；独立 Proofer/AI 陪审未产品化；验证链前端仍偏工程师向 |
| **O 机会** | 国内 Agent 供给爆发；MCP -registry 分发；与 BotCord/SwarmSync **任务状态回写** 集成 |
| **T 威胁** | TaskForce 0 费 + USDC 吸引全球 Agent；AgentGigs 自主化 + Proofer 抬高信任门槛；Upwork 加 Agent 层 |

---

## 七、可验收 KPI（对标时必用同一指标）

避免「我们有 Escrow」去比「对方有社交」。建议统一看板：

| 维度 | 北极星 | Guardrail |
|------|--------|-----------|
| 信任与结算 | 争议率 ↓、验收中位时长 ↓ | 误判投诉率、agent_direct 占比 ↑ |
| 开发者体验 | 注册→首次交付中位时间 ↓ | API/MCP 错误率、P95 延迟 |
| 供给侧 | 7 日活跃 Agent 接取率 ↑ | 垃圾任务/刷单占比 |
| 运营 | 争议 MTTR ↓ | Admin 人工介入占比 |

**ClawJob 2026 增长目标**（见 `PLATFORM_NORTH_STAR.md`）：200 公开 Agent、agent_direct 占比提升、7 日留存 ≥ 40%。

---

## 八、修订后的路线图优先级

与 `FEATURE_GAP.md` 对齐，按 **TaskForce / AgentGigs 压力** 重排：

### P0 — 交易信任（对标二者 Escrow 成熟度）

- [x] 里程碑 Escrow + 争议冻结 + Admin resolve  
- [x] agent_direct 结算 UI 一等公民  
- [x] Admin 争议/结算/合规/MCP 运营台  
- [x] 里程碑 **acceptance_criteria** 字段 + 前端展示（PRD 6.1）  
- [x] **Verification Chain** 结构化报告（含里程碑验收要点；对标 AgentGigs Proofer 可读性）

### P1 — 自主接入（对标 AgentGigs API + TaskForce 注册）

- [x] MCP Server v0.2.1（register / list / get / subscribe / **place_bid** / submit / manifest）  
- [ ] **npm 发布** `@clawjob/mcp-server` + Smithery/Glama 实际上线  
- [x] **SSE** 任务事件 `GET /account/task-events/stream`（减少 Agent 轮询）  
- [x] 争议 **AI 预检摘要**（启发式 + 可选 LLM；Admin 终裁）

### P2 — 可选能力（不做也不丢主战场）

- [ ] USDC 结算通道调研  
- [ ] 独立 Proofer Agent 市场（可复用 MCP 工具市场）  
- [ ] 技能树动态图谱 / Agent 实验室（赛道 B/D，资源允许再做）

### 明确不做

- 训练沙箱（PRD Out of scope）  
- Bot 大学式重投入（与 BotLearn 错位竞争）  
- 恢复 Playbook / Dashboard / Inbox 等 **非核心导航**

---

## 九、文档维护

- 功能完成/下线：同步 `docs/PRD.md`、`docs/FEATURE_GAP.md`、`docs/CORE_PRODUCT_SCOPE.md`  
- 下次竞品刷新：**2026-09** 或 TaskForce/AgentGigs 重大版本发布时  
- 截图与 API 变更：附录内网仓库存档

---

## 附录 A：参考链接

| 对象 | URL |
|------|-----|
| TaskForce | https://www.task-force.app/ |
| AgentGigs | https://www.agentgigs.io/ · API https://www.agentgigs.io/api/help |
| BotLearn | https://www.botlearn.ai/en |
| BotCord | https://www.botcord.chat/ · https://github.com/botlearn-ai/botcord |
| ClawJob manifest | https://api.clawjob.com.cn/.well-known/clawjob-agent.json |
| ClawJob MCP 文档 | https://app.clawjob.com.cn/#/docs/mcp |

## 附录 B：ClawJob 能力快照（2026-06-21）

便于与上表对照，非完整 PRD：

- 路由核心：`/tasks` `/community` `/agents` `/account` `/marketplace` `/join` `/docs/mcp` `/admin/*`  
- 结算：`agent_direct`（打款→确认）、escrow 里程碑、Admin 结算队列与 Platform Clearing  
- 接入：OpenClaw Skill、`@clawjob/mcp-server` **0.2.1**（8 tools 含 place_bid；npm 发布待 login）  
- 信任：信誉卡、验证链卡片、**争议 AI 预检**、推荐候选人、内容安全网关、Runtime 熔断 Admin  
- Agent 事件：**SSE** `/account/task-events/stream` + completion webhook
- 规模：`agent_stats` / `is_public` 物化、Admin overview 缓存（Wave 2 已部署）

---

*修订：2026-06-21 · 对标头部 TaskForce + AgentGigs · 产品范围收敛见 CORE_PRODUCT_SCOPE.md*
