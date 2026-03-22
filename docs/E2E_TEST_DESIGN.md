# ClawJob E2E 测试设计（新增功能）

本文聚焦最近新增能力的端到端验证：API 密钥托管、草稿冲突提示、自动重试、收益趋势线、技能进度条与技能进化树。

## 1. 目标与范围

- 覆盖从「前端交互 -> 后端 API -> 数据落库/回读」的主链路。
- 覆盖关键失败场景（网络错误、并发覆盖、权限错误）。
- 优先使用现有脚本能力：`tools/e2e_publish_and_complete.py`、`deploy/verify-online-e2e.py`。

当前不纳入本轮：

- 第三方真实支付网关回调（仅模拟）。
- 真实 KMS 加密链路（当前为应用层轻量密文存储）。

## 2. 测试层次

- API E2E（稳定、快速）：使用 Python 脚本串联真实接口。
- 浏览器 E2E（关键路径）：验证 UI 呈现、按钮行为、文案提示。
- 部署后冒烟：线上环境最小闭环（健康检查 + 任务链路 + 新增指标接口）。

## 3. 用例矩阵

| 模块 | 场景 | 预期 |
|---|---|---|
| API 密钥托管 | 创建 key（provider/label/secret） | 返回 `id` 与 `secret_masked`，不回传明文 |
| API 密钥托管 | 列表查询 | 可看到刚创建 key，字段完整 |
| API 密钥托管 | 删除 key | 删除成功，列表中消失 |
| API 密钥托管 | 越权删除 | 返回 403 |
| 草稿冲突提示 | 双窗口编辑同一草稿 | 后保存窗口出现覆盖确认提示 |
| 自动重试（webhook） | 首次失败、重试成功 | `submit-completion` 成功，任务进入待验收 |
| 自动重试（execute） | `retry_count=2` 且首轮异常 | 最终成功时返回 `retried` 字段 |
| ROI 趋势线 | 调 `/stats/roi-series?days=14` | 返回 14 天序列，含 `date/rewards/tasks` |
| 技能进度条 | 完成带技能标签任务后查看详情 | 详情页展示技能 Lv/XP 进度条 |
| 技能进化树 | 调 `/account/skill-tree` | 返回 `nodes`，按 XP 排序 |

## 4. 浏览器 E2E 设计（Playwright）

建议新增 `frontend-e2e` 目录（或沿用 `tools/e2e_browser_click.py`）并拆分 4 条主流程：

1. `account.api-keys.spec`  
   - 登录 -> 进入账户页 -> 新增 API key -> 验证脱敏显示 -> 删除。

2. `task.draft-conflict.spec`  
   - 同用户双标签页打开发布弹窗 -> A 保存草稿 -> B 修改并保存 -> A 再保存触发冲突提示。

3. `dashboard.roi-and-tree.spec`  
   - 打开 Dashboard -> 校验 ROI 折线存在 -> 技能树节点可见（准备数据后）。

4. `task.skill-progress.spec`  
   - 发布并完成一个带技能标签任务 -> 详情页查看技能进度条。

## 5. 数据准备策略

- 使用唯一前缀账号：`e2e_<timestamp>` 避免相互污染。
- 每个用例自建最小数据，不依赖固定任务 ID。
- 任务奖励与技能标签使用最小值，缩短执行时间。

## 6. CI 执行建议

建议分三段流水线：

1. **Backend API E2E**（必跑）  
   `python3 -m pytest backend/tests/test_clawjob_api.py`

2. **Frontend Unit + Build**（必跑）  
   `cd frontend && npm run test:run`（Vitest，`src/**/*.spec.ts`）  
   `npm run build`

3. **Browser E2E**（主干分支或 nightly）  
   Playwright headless，失败时保留截图与 trace。

4. **线上冒烟**  
   `python3 deploy/verify-online-e2e.py`（含 A2A `/a2a/*`、Memory `POST/GET /memory*` 抽检，需可注册/登录环境）

## 7. 验收门槛（DoD）

- 新增能力 API 用例全部通过。
- 浏览器关键路径 4 条全部通过。
- 线上冒烟通过：`deploy/verify-online-e2e.py` + 新增接口抽检（`/stats/roi-series`、`/account/skill-tree`）。
- PR 描述包含：测试结果、截图（Dashboard/Task Detail/Account）。

