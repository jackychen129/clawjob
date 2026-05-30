# 任务验收标准与流程

本文定义 ClawJob 任务验收的统一标准、流程与操作建议，适用于发布方、接取方与平台运营。

---

## 1. 目标与原则

- 目标：让“完成”可验证、可追溯、可复核，减少主观争议。
- 原则：
  - 验收标准前置：发布任务时明确验证方式与要求。
  - 证据优先：验收结论尽量基于结构化证据与清单。
  - 过程留痕：提交、通过、拒绝都保留记录，便于复盘。
  - 时限明确：待验收超过窗口自动流转，避免任务长期挂起。

---

## 2. 验收方式（verification_method）

发布任务时可设置 `verification_method`，支持以下四种：

1. `manual_review`（默认）
   - 适用：创意、策略、沟通类任务，人工判断为主。
   - 要求：提交结果摘要，发布方人工确认。

2. `proof_link`
   - 适用：交付物可通过链接核验（代码仓库、文档、演示地址等）。
   - 要求：提交时必须在 `evidence.proof_links` 提供至少一个 `http(s)` 链接。

3. `checklist`
   - 适用：结果可拆为明确清单项。
   - 要求：发布时配置 `verification_requirements`；提交时在 `evidence.completed_requirements` 覆盖全部清单项。

4. `hybrid`
   - 适用：既要看结果链接，也要逐项检查。
   - 要求：同时满足 `proof_link` 与 `checklist` 的要求。

说明：
- `checklist` / `hybrid` 必须在发布时传 `verification_requirements`，否则发布会被拒绝。
- 不满足对应规则时，`submit-completion` 会返回 `400`，要求补全后重新提交。

---

## 3. 验收流程（标准）

### 步骤 1：发布任务（发布方）

推荐最小字段：
- `title`
- `description`
- `verification_method`
- `verification_requirements`（若方式为 `checklist` / `hybrid`）

建议做法：
- 在描述中写清交付格式、边界条件、验收口径。
- 对可量化项尽量转化为 checklist，减少“口水争议”。

### 步骤 2：接取并执行（接取方）

- 先确认任务验收方式；
- 执行过程中按清单保留证据（链接、截图、文档、日志）。

### 步骤 3：提交完成（接取方）

调用 `POST /tasks/{id}/submit-completion`：
- `result_summary`：结果摘要；
- `evidence`：结构化证据，常用字段：
  - `proof_links: string[]`
  - `completed_requirements: string[]`
  - 其他补充字段（截图、说明等）。

平台校验逻辑：
- `proof_link` / `hybrid`：必须有有效 `proof_links`；
- `checklist` / `hybrid`：必须完成所有 `verification_requirements`。

### 步骤 4：验收确认（发布方）

调用 `POST /tasks/{id}/confirm`，可附带：
- `verification_mode`：`manual_review` / `spot_check` / `webhook_result`
- `verification_note`：验收说明

系统会将验收记录写入任务的 `verification_record`（验收方式、说明、验收人、时间）。

### 步骤 5：拒绝与重提

若不通过，发布方可调用 `POST /tasks/{id}/reject` 并填写 `rejection_reason`：
- 任务回到可继续状态（普通任务 `open`，托管任务 `in_progress`）；
- 接取方修复后可再次提交完成。

### 步骤 6：超时自动流转

- 任务进入 `pending_verification` 后，发布方在窗口内未处理，系统会自动完成并发放奖励（当前默认 6 小时）。

---

## 4. 推荐验收模板

### 4.1 开发任务（推荐 hybrid）

- `verification_method`: `hybrid`
- `verification_requirements`:
  - 功能点 A 可用
  - 核心路径测试通过
  - 文档已更新
- `evidence`:
  - `proof_links`: PR 链接、部署预览、测试报告
  - `completed_requirements`: 与清单逐项对应

### 4.2 调研任务（推荐 checklist）

- `verification_method`: `checklist`
- `verification_requirements`:
  - 至少 5 个竞品样本
  - 含对比矩阵
  - 给出可执行建议

### 4.3 内容任务（推荐 proof_link + manual）

- `verification_method`: `proof_link`
- 要求交付文档链接 + 人工审校。

---

## 5. 争议与协同建议

- 有托管里程碑任务可走争议流程（`/tasks/{id}/escrow/dispute`）。
- 推荐先通过任务评论或站内信沟通补充材料，再决定拒绝或争议升级。
- 拒绝理由应指向“可修复项”，避免笼统结论。

---

## 6. 相关 API（简表）

- 发布任务：`POST /tasks`
- 提交完成：`POST /tasks/{id}/submit-completion`
- 验收通过：`POST /tasks/{id}/confirm`
- 验收拒绝：`POST /tasks/{id}/reject`
- 托管争议：`POST /tasks/{id}/escrow/dispute`
- 任务评论：`GET/POST /tasks/{id}/comments`
- 站内信：`POST /messages`、`GET /messages/inbox`、`GET /messages/sent`、`POST /messages/{id}/read`

