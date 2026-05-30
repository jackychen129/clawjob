# PRD 未完成功能：详细计划与上线节奏

> 依据：`docs/PRD.md`（实现状态表）、`docs/FEATURE_GAP.md`（缺口总览）。若两处表述不一致，**以 FEATURE_GAP 与代码为准**。

## 一、先澄清：PRD 表里「未做」的其实不多

`PRD.md` 应用端 23 项中，**多数已标为已实现**（含争议证据、`acceptance_criteria`、版本化发布等）。当前仍值得投入研发的，主要集中在：

| 类别 | 内容 | 依据 |
|------|------|------|
| **部分实现** | 技能进化树（缺动态图谱、技能折旧）、ROI（有益收曲线，非交易所级 K 线）、自动重试（Webhook 有，Agent 执行侧未统一） | FEATURE_GAP §一 |
| **未实现（独立能力）** | Agent 实验室（Dark / CoT / 状态机独立页） | FEATURE_GAP §一、PRD 应用端 #7 |
| **不做** | 训练沙箱 | PRD 明确 Out of scope |
| **API 有、主站弱** | Workflow 图形化编排、验证链结构化报告、熔断 reset/告警配置、Memory/Tools 收敛单页、平台 Clearing 运营工具 | FEATURE_GAP §二 |

下文按 **业务价值 × 可交付性** 排序，**不是**严格按 PRD 序号。

---

## 二、分阶段路线图（建议）

### P0：稳定性与可观测（任何功能的前置）

- **CI 门禁**：`main` / PR 自动跑后端 pytest、前端 Vitest、构建、Playwright 冒烟（见 `.github/workflows/ci.yml`）。
- **线上探针**：`tools/monitor_probe.py` + 定时 workflow（见 `docs/MONITORING_MINIMUM.md`）。
- **发布/回滚**：按 `docs/RELEASE_CHECKLIST.md` 执行；发布后 `python3 tools/verify_online_e2e.py`。

**验收**：合并到 `main` 后 GitHub Actions 绿；生产 API 冒烟脚本通过。

### P1：PRD「体验缺口」里性价比最高的一批

1. **验证链（Verification Chain）可读性**  
   - 现状：详情可拉 JSON。  
   - 目标：任务详情内 **卡片化**（层级/状态/失败原因摘要），减少纯 JSON。  
   - 依赖：后端字段已有时，以前端为主。

2. **Workflow DAG（前端）**  
   - 现状：规划/绑定 API 已有。  
   - 目标：最小可用 **只读拓扑图 + 节点状态**（不必一上来全拖拽编辑器）。

3. **Agent 执行侧重试（产品化）**  
   - 与 Webhook 重试对齐叙事：在任务详情或执行记录中展示 **重试次数/下一次重试时间**（若后端已有字段则只做展示）。

### P2：差异化与长期投入

- **技能折旧 + 动态技能图谱**：需数据模型与展示设计，工作量较大。  
- **Agent 实验室独立页**：Dark 主题、CoT、状态机——需单独信息架构与后端配合。  
- **技能包有偿分享 / 法币或点数结算链**：涉及支付与合规，单独立项。  
- **平台 Clearing 账户 UI**：密钥鉴权，适合 **内部运营工具** 或 CLI，不与普通超管混用。

---

## 三、更新「线上环境」的标准流程（代码已推送后）

> 本仓库无法替你 SSH 上服务器；以下为你或运维在 **部署机** 上的固定步骤。

1. **拉取最新 `main`**（部署目录示例 `/opt/clawjob`）：  
   `git fetch origin && git checkout main && git pull origin main`

2. **按现有方式重建/重启**（若使用 Docker）：  
   `cd deploy && docker compose -f docker-compose.prod.yml up -d --build`  
   （若你方 `compose` 文件名不同，以实际为准，见 `docs/OPEN_SOURCE_AND_PRODUCTION.md`。）

3. **验证**：  
   - `python3 tools/verify_online_e2e.py`  
   - 可选：`python3 tools/monitor_probe.py`  
   - 浏览器：`cd frontend && npm run e2e`（或对 `PLAYWRIGHT_BASE_URL` 指到生产前端）

4. **若失败**：按 `docs/RELEASE_CHECKLIST.md` 回滚到上一稳定 tag/commit。

---

## 四、2 小时工作内容（可直接照表执行）

> 目标：在 **不新开大块需求** 的前提下，把「发布链路 + 监控 + 冒烟」跑通，并留 30～40 分钟给 **一个** 小改进或问题修复。

| 时段 | 动作 | 产出 |
|------|------|------|
| **0:00–0:25** | 本地确认：`cd backend && PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py tests/test_data_iteration_engine.py -q`；`cd frontend && npm run test:run && npm run build` | 本地与 CI 行为一致 |
| **0:25–0:40** | `git pull` / `git push`：确保 `main` 含 CI、监控、发布清单；打开 GitHub → Actions，确认 **CI** 与（若已启用）**Monitor** 最近一次成功 | 主干可发布状态 |
| **0:40–1:10** | **服务器**：拉代码、重建容器（见第三节）；执行 `python3 tools/verify_online_e2e.py`；抽查首页与 `/#/tasks` | 线上与文档一致 |
| **1:10–1:40** | **选一项** P1 小步（择一即可）：① 验证链卡片原型（仅前端 mock + 真实 API 字段对接）；② 或给 `monitor_probe` 增加 Slack/邮件 webhook（若已有密钥）；③ 或修复当日 CI/探针暴露的一个真实失败 | 可合并的 PR 或 hotfix |
| **1:40–2:00** | 记录：发布 commit、探针结果、未解决问题记入 `docs/FEATURE_GAP.md` 或 Issue | 下一轮排期有据 |

**若 2 小时内服务器不可操作**：把「0:40–1:10」换成「在预发/staging 或本机 `docker compose` 跑通同样命令」，并保留第三节清单待窗口期执行。

---

## 五、下一步建议（你确认优先级后可拆 Issue）

1. **Issue：验证链卡片化**（前端 + 少量类型）  
2. **Issue：Workflow 只读 DAG**（前端图 + 现有 API）  
3. **Issue：Agent 实验室 MVP**（仅路由 + Dark 模式开关 + 占位说明）  
4. **Issue：执行侧重试可观测**（后端字段确认 + 前端展示）

---

*文档随迭代更新；完成某项后请同步 `docs/PRD.md` 状态表与 `docs/FEATURE_GAP.md`，避免「已实现/未实现」漂移。*
