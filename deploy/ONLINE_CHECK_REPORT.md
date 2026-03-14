# 线上功能检查报告

**检查时间**: 2025-03-13  
**API**: https://api.clawjob.com.cn  
**前端**: https://app.clawjob.com.cn  

---

## 最新验证（2026-03-14）— 全部通过

**环境**: `http://8.216.64.80`（由 deploy/.deploy_env 的 SERVER_IP 决定）

| 项目 | 地址 | 状态 |
|------|------|------|
| 官网 | http://8.216.64.80/ | ✅ 可访问 |
| 任务大厅 | http://8.216.64.80:3000 | ✅ 可访问 |
| 后端 API | http://8.216.64.80:8000 | ✅ 健康检查通过 |

**API 全流程**（`verify-deployed.py`）：Health、/tasks、/candidates、register-via-skill、/account/me、POST /tasks、/agents/mine、/account/receiving-account、/account/commission — **All checks passed.**

**E2E**（`verify-online-e2e.py`）：13 项全部通过（含注册、发布任务、接取、前端页面可达）。

**本次修复**：`deploy/verify-deployed.py` 原使用 `POST /auth/register`（需 verification_code），已改为 `POST /auth/register-via-skill`，与 E2E 一致，验证脚本在无验证码环境下可一次通过。

---

## 问题与修复（2025-03-13）

**根因**：后端日志报 `password authentication failed for user "clawjob"`。Postgres 由 docker-compose 创建，用户/库为 `agentarena`，但容器内 `DATABASE_URL` 指向用户/库 `clawjob`，导致所有依赖 DB 的接口 500。

**处理**：在服务器 `/opt/clawjob/deploy/.env` 中将 `DATABASE_URL` 改为使用 `agentarena` 用户与库（与 docker-compose.prod.yml 一致），并执行 `docker compose -f docker-compose.prod.yml up -d --force-recreate backend`。修复后 `/health`、`/tasks`、`/auth/login`、`/auth/send-verification-code` 等接口已恢复正常。

---

## 检查结果汇总（修复前）

| 功能 | 状态 | 说明 |
|------|------|------|
| API 健康检查 GET /health | ✅ 通过 | 200，relational_db 等正常 |
| Google OAuth 状态 GET /auth/google/status | ✅ 通过 | 200，configured=True |
| 发送验证码 POST /auth/send-verification-code | ❌ 500 | Internal Server Error |
| 用户注册 POST /auth/register | ❌ 500 | Internal Server Error（带验证码请求同样 500） |
| 用户登录 POST /auth/login | ❌ 500 | Internal Server Error |
| 任务大厅 GET /tasks | ❌ 500 | Internal Server Error |
| 候选者列表 GET /candidates | ❌ 500 | Internal Server Error |
| Agent 注册 POST /agents/register | ⏭️ 未测 | 依赖登录 Token，因登录 500 无法获取 |
| 前端页面 | ✅ 可访问 | 首页、登录/注册弹窗正常，点击登录后显示 "Login failed" |

## 结论

- **用户注册、登录、Agent 注册** 在线上当前**不可用**：认证相关接口以及依赖数据库的公开接口均返回 **500 Internal Server Error**。
- 前端可正常打开，登录/注册表单可操作，但请求后端时得到 500，前端会显示 "Login failed" 等错误。
- `/health` 与 `/auth/google/status` 正常，说明服务进程与部分逻辑可用，问题很可能出在**数据库连接或会话**（如 `get_db()` 依赖的 Session、表结构缺失等）。

## 建议排查步骤

1. **查看线上后端日志**  
   对 500 请求查看 uvicorn/gunicorn 或应用日志中的 traceback，确认是 DB 连接异常、缺失表/列，还是其它未捕获异常。

2. **确认数据库**  
   - 生产环境 `DATABASE_URL` 是否正确、网络是否可达。  
   - 执行 `init_db()` 或迁移，确认存在 `users`、`verification_codes`、`tasks`、`agents` 等表及所需列（如 `Task.submitted_at`、`verification_deadline_at` 等）。

3. **验证码与注册**  
   - 若希望 E2E 脚本在线上跑通注册，可在服务器环境设置 `VERIFICATION_CODE_DEV=123456`（与 `deploy/verify-online-e2e.py` 中使用的验证码一致）。  
   - 修复 500 后，脚本会先调用 `POST /auth/send-verification-code`，再带 `verification_code` 调用 `POST /auth/register`。

4. **重新跑 E2E**  
   修复后端后执行：  
   `CLAWJOB_API_URL=https://api.clawjob.com.cn CLAWJOB_FRONTEND_URL=https://app.clawjob.com.cn python3 deploy/verify-online-e2e.py`

## 本次修改

- **deploy/verify-online-e2e.py**：注册前先调用 `POST /auth/send-verification-code`，并在 `POST /auth/register` 中带上 `verification_code`（优先使用环境变量 `VERIFICATION_CODE_DEV`，否则默认 `123456`），避免 422 Field required。
