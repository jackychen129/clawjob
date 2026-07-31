# ClawJob 系统优化策略（Admin + 10k Agent）

> 目标：支撑 **10,000 公开 Agent** 规模，后台达到行业一线运维体验（低延迟聚合、可扩展队列、一致交互模式）。

## 一、现状诊断

| 层 | 已完成 | 瓶颈 |
|----|--------|------|
| **前端 Admin** | 9 子路由 + AdminLayout + 共享 Dialog | 争议/结算/KYC 无分页；各页重复 reload 逻辑 |
| **后端 Admin** | `/admin/overview` 聚合意图 | overview 运行时 bug；15+ COUNT 无缓存 |
| **Settlement** | agent_direct 队列 | 全表扫描 `output_data` + Python 过滤 |
| **公开 Agent** | Redis 缓存 + yield_per | 计数仍 O(n) Python 过滤，无 `is_public` 列 |
| **信誉** | Redis 5min + SQL 聚合 | recommend-candidates 未 bulk |

## 二、优化路线图（四波）

### Wave 1 — 正确性 + 热点路径（✅ 已执行）

- [x] 修复 `/admin/overview` 未定义变量
- [x] `admin_overview` service + Redis snapshot（120s TTL）
- [x] Settlement 改 PostgreSQL JSON 过滤 + 分页 SQL + 60s 计数缓存
- [x] Workspaces `seats_used` 子查询消 N+1
- [x] `useAdminPaginatedList` + `AdminPagination` + 争议/结算/KYC/提现分页
- [x] `006_admin_scale_indexes.sql`（system_logs / task_subscriptions / settlement_mode）
- [x] KYC/提现/争议操作后 invalidate overview snapshot

### Wave 2 — 数据模型（10k 核心）（进行中）

- [x] 迁移 `agents.is_public` 物化列 + 索引 `007_agent_is_public.sql`
- [x] 写入点：注册 / Skill 注册 / cleanup / system agent sync
- [x] `count_public_agents` / 分页改 SQL `WHERE is_public`
- [x] `backfill_agent_is_public.py` + init_db 自动回填
- [x] `recommend-candidates` 接入 `compute_bulk_reputations` + `is_public` 过滤
- [x] `agent_stats` 预聚合表（points、completed、published、assigned）
- [x] `tasks.is_public_listing` 物化 + SQL COUNT
- [x] `/candidates`、`/leaderboard` 改读 `agent_stats`
- [ ] 完善 cleanup / 脚本路径的 cache 失效

### Wave 3 — 架构演进

- [ ] 拆分 `admin.py` → `routers/admin/{overview,compliance,settlements,...}.py`
- [ ] 抽取 `AdminDataTable` + `AdminQueuePanel` 组件
- [ ] 合并 `/admin/metrics` → `/overview`，删除 `OpsView.vue`
- [ ] Insights retention 矩阵前端展示 + 查询去重

### Wave 4 — 体验 polish

- [ ] 争议任务链到 Task 详情 + 证据 JSON 预览
- [ ] 全局 Admin 搜索 / CommandPalette 深链
- [ ] 队列筛选（phase、日期、关键词）
- [ ] 操作 toast + 乐观更新 + 错误 surfacing

## 三、SLA 目标

| 端点 | 当前（估） | Wave 1 后 | Wave 2 后 |
|------|-----------|-----------|-----------|
| `GET /admin/overview` | 500 / 慢 | <200ms（缓存 hit） | <100ms |
| `GET /admin/settlements/pending` | O(tasks) 全表 | O(page) 索引 JSON | O(page) |
| `GET /candidates` | 缓存 hit 快 | 同左 | SQL 分页 |
| `GET /stats` | 120s 缓存 | 同左 | 增量 refresh |

## 四、技术原则

1. **读多写少走缓存**：overview / public stats / settlement counts，TTL + 写路径失效。
2. **列表必须 SQL 分页**：禁止 Python 全表过滤后再 slice。
3. **Admin UI 一套模式**：composable 分页 + 统一 skeleton/empty/pagination。
4. **物化优于运行时推导**：公开标记、聚合统计落库。
5. **小步可部署**：每波独立 PR，生产可灰度验证。

## 五、验收清单

- [ ] `verify-deployed.py` 全绿
- [ ] `/admin/overview` 200 + `agents.public` / `agents.goal`
- [ ] 争议/结算队列 >50 条可翻页
- [ ] pytest admin + settlement 用例
- [ ] 生产 `006` 迁移已执行

---

*最后更新：Wave 1 执行中*
