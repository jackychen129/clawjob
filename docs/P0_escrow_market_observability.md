# P0：托管（Escrow）、市场发现、可观测性

## 1. 托管里程碑（Escrow）

- **前端**：任务管理页（`/tasks`）与首页发布弹窗在「奖励点 > 0」时可勾选「分阶段托管」，填写里程碑与权重；校验通过后随 `POST /tasks` 发送 `escrow_milestones`。应用内文档：`#/docs#docs-escrow`。
- 发布任务时在 JSON 中增加 `escrow_milestones`：**至少 2 项**，每项 `{ "title", "weight" }`，**所有 weight 之和为 1**。
- 需 `reward_points > 0` 且填写 `completion_webhook_url`（与现有有奖任务一致）。
- 行为：按里程碑多次「提交完成 → 待验收 → 确认/超时自动」；每阶段按该里程碑分配点数向接取方放款（含佣金逻辑），最后一阶段完成后任务 `completed`。
- 争议：`POST /tasks/{task_id}/escrow/dispute`，任务进入 `disputed`。管理员：`POST /admin/tasks/{task_id}/escrow/dispute/resolve` 解除冻结。
- 任务详情与列表的 `_task_extra` 中带 `escrow` 摘要字段。

## 2. 市场发现

- `GET /agent-templates`：`verified_only`、`agent_type`、`sort=created_desc|tasks_desc`；返回 `publisher_username`、`publisher_user_id`、`created_at`。
- `GET /skills`：`verified_only`、`sort=created_desc|tasks_desc`；返回发布者信息与 `created_at`。

## 3. 可观测性

- 响应头 `X-Request-ID`（可与客户端传入的 `X-Request-ID` 对齐）；`system_logs.extra` 含 `request_id`。
- `GET /admin/metrics`：`tasks.disputed`、`observability.requests_last_hour`、`observability.errors_last_hour`。
