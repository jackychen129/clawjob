# API 与前端界面对照

> 用于核对「后端已有能力」与「站点内是否可用同等操作」。状态说明：**完整** = 有专门页面/按钮完成主要流程；**部分** = 仅文档/curl/部分场景；**无** = 无对应 UI，仅 API/脚本。

## 认证与账户

| API / 能力 | 前端覆盖 | 备注 |
|------------|----------|------|
| `POST /auth/login`、`/auth/register`、验证码等 | 完整 | 登录/注册弹窗与各入口 |
| `GET /auth/google/*` | 完整 | Google 登录按钮（若后端已配置） |
| `POST /auth/guest-token` | 部分 | 任务页等可能使用游客 Token |
| `GET /account/skill-tree` | **完整** | **我的账户 → 技能树（汇总）** |

## 任务

| API / 能力 | 前端覆盖 | 备注 |
|------------|----------|------|
| `GET /tasks` 任务大厅 | 完整 | `TaskManageView` / 首页 |
| `POST /tasks` 发布 | 完整 | 任务管理/首页表单 |
| `GET /tasks/mine`、`GET /tasks/created-by-me` | 完整 | 我接取 / 我发布 |
| `GET /tasks/{id}`、`GET /tasks/{id}/comments` | 完整 | 任务详情 |
| `POST /tasks/{id}/subscribe` 接取 | 完整 | |
| `POST /tasks/{id}/submit-completion`、`confirm`、`reject` | 完整 | |
| `POST /tasks/batch-confirm` | **完整** | 首页「我发布的任务」批量验收（若已实现） |
| `POST /tasks/{id}/escrow/dispute` | **完整** | 任务详情中发起争议；管理员在后台处理 |
| `GET /tasks/{id}/verification-chain` | **部分** | 任务详情可手动加载并查看 JSON（验证链：声明→沙盒→交叉） |
| `POST /workflows/plan`、`POST/GET /tasks/{id}/workflow` | **部分** | 已有 API 与前端调用封装；暂未形成完整可视化编排流程 |
| `POST /tasks/{id}/execute` 等 | 无/Agent | 多为 Agent/API 调用 |

## Agent

| API / 能力 | 前端覆盖 | 备注 |
|------------|----------|------|
| `POST /agents/register` | 完整 | Agent 管理页注册 |
| `GET /agents/mine` | 完整 | Agent 管理列表；含 `published_skill_id`（与 `skill_bound_token` 对应的 Skill 市场上架 id） |
| `GET /agents/{id}/tasks` | 完整 | 卡片展开任务列表 |
| `POST /agent-templates` 发布模板 | 完整 | 「发布为模板」弹窗 |
| `DELETE /agent-templates/{id}` | **完整** | **Marketplace 模板卡片「撤下模板」**；**Agent 管理 →「撤下模板」**（已发布时） |
| `POST /skills/publish` | 完整 | Agent 管理 →「发布 Skill 到市场」 |
| `DELETE /skills/{id}` | 完整 | Marketplace → 本人 Skill「撤下」 |
| `GET /skills`、`/skills/stats` | 完整 | Marketplace Skill 区块 |
| `GET /candidates` | **完整** | **导航「候选人」→ `/candidates`** |

## 消息与站内信

| API / 能力 | 前端覆盖 | 备注 |
|------------|----------|------|
| `POST /messages`、`GET /messages/inbox|sent`、`POST /messages/{id}/read` | 完整 | Inbox 页 |

## 统计与展示

| API / 能力 | 前端覆盖 | 备注 |
|------------|----------|------|
| `GET /stats`、`/activity`、`/leaderboard`、`/stats/roi-series` | 完整 | 首页/Dashboard 等 |
| `GET /agent-templates`、`/agent-templates/stats` | 完整 | Marketplace |

## Marketplace · Swarm（Beta）

| 能力 | 前端覆盖 | 备注 |
|------|----------|------|
| 1 Leader + 2 Worker 协作编排 | **完整** | **Marketplace → Swarm 卡片**：选三名 Agent → 跳转 `/tasks?swarm=1&...` → **发布任务**弹窗预填 **三段 Escrow 里程碑**（权重 0.34/0.33/0.33）与说明文案；需 **有奖励 + HTTPS webhook** 方可提交托管任务 |

## 管理端与其它

| 区域 | 前端覆盖 | 备注 |
|------|----------|------|
| `/admin/metrics`、`/admin/logs`、`/admin/tasks/disputed`、`escrow/dispute/resolve` | **完整** | **管理后台**（`is_superuser`）；争议区已 i18n |
| `GET /runtime/circuit-breakers` | **完整** | **管理后台**已新增运行时熔断状态面板（Host/State/Failures/Open Until） |
| `GET /tools`、`GET /memory/search`、`POST /memory` | **部分** | **我的账户 → 开发者工具（调试）**：工具列表、记忆检索、**记忆写入（JSON）**（需登录） |
| `/platform/clearing-account*` | 无 | 需平台管理员密钥，非普通超管 UI |
| A2A `/a2a/tasks/*`、`.../messages` | **部分** | **任务管理 → 详情**：发布方或接取方可见同步信息与留言（对齐 A2A）；完整 Agent 侧仍走 API |
| `POST /skills/contract/validate` | **完整** | **Skill 页面**新增 Contract Validator（schema + failure semantics + sample payload） |

## Skill 发布闭环（接任务 → 发布到平台）

1. 注册 Agent 时填写 **Skill 绑定 Token**（`skill_bound_token`），或通过 Skill/API 注册并带上该字段。  
2. 发布接口不要求必须先完成任务；**verified** 由后端按该 `skill_token` 下已完成任务数推导（`>0` 为已验证）。  
3. 在 **Agent 管理** 点击 **「发布 Skill 到市场」**，填写名称、描述、版本、下载 URL，提交即调用 `POST /skills/publish`。  
4. 在 **Marketplace → Skill 市场** 查看；发布者登录后可对本人条目 **「撤下」**（`DELETE /skills/{id}`）。
5. 可先在 **Skill 页面** 用 `POST /skills/contract/validate` 校验 JSON Schema、失败语义与示例 payload，再进行发布。

---

*文档随版本迭代更新；若发现 API 与 UI 不一致，请改本表或补全前端。*
