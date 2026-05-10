# PRD 缺口执行计划（2026Q2）

> 目标：把「还没做 / 没做完整」的能力拆成可交付步骤，并且每步都能验收。

## 1) 真实缺口（按优先级）

### P0（应先完成）

1. **Agent 执行侧重试可观测（补齐）**
   - 现状：`/tasks/{id}/execute` 支持 `retry_count`，但结果追踪不完整。
   - 目标：任务详情可见最后一次执行结果（重试次数、时间、成功/失败）。
   - 验收：`output_data.last_execute` 有稳定字段；失败也有记录。

2. **Verification Chain 卡片化（可读性）**
   - 现状：有数据，前端可读性一般。
   - 目标：任务详情按声明/预检/交叉拆卡片展示，失败原因聚合。
   - 验收：非 JSON 原文也能看懂问题点。

3. **Workflow DAG 只读拓扑（统一体验）**
   - 现状：后端能力已具备，前端已有基础图。
   - 目标：任务详情内统一显示节点、依赖、状态与不可用原因。
   - 验收：发布方/接取方都可直观看流程。

### P1（P0 完成后）

4. **Runtime Circuit Breaker 运维增强**
   - 现状：已可查看并操作开关。
   - 目标：补阈值与告警配置视图（最小可用）。
   - 验收：可配置 + 可追踪变更。

5. **Memory / Tools 开发者操作完善**
   - 现状：已有查询与部分调试入口。
   - 目标：补“创建工具向导 / Agent 调用工具向导 / 历史记录”。
   - 验收：非研发用户也能按 UI 完成调试。

### P2（长期）

6. **技能折旧 + 动态技能图谱**
7. **Agent 实验室（独立产品级，不是仅本地 preset）**
8. **Skill 商业化结算链（付费/分成/合规）**
9. **Clearing Account 运营后台（密钥体系独立）**

## 2) 分步实施（本轮开始执行）

### Step 1（已完成）

- 已实现：`/tasks/{id}/execute` 成功/失败都会写入 `task.output_data.last_execute`：
  - `retried`（重试次数）
  - `at`（时间）
  - `ok`（是否成功）
  - `error`（失败时摘要）
- 已补测试：`test_execute_task_retry_observability_saved`。

### Step 2（下一步）

- 实现 Verification Chain 卡片化：
  - 把当前字段映射为“通过/警告/阻断”三层。
  - 在任务详情给出失败原因摘要区。

### Step 3

- Workflow DAG 视图统一：
  - 统一节点状态颜色、不可用原因提示。
  - 增加空状态/错误状态显示。

## 3) 本轮验收命令

- 后端（核心）：
  - `cd backend && PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py::test_execute_task_retry_observability_saved -q`
- 回归（建议）：
  - `cd backend && PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py tests/test_data_iteration_engine.py -q --tb=no`
  - `cd frontend && npm run test:run && npm run build`

