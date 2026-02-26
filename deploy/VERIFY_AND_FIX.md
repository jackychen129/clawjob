# 部署后验证与常见问题修复

## 一键：验证并自动修复直到通过（推荐）

在本机（能 SSH 到服务器的环境）执行：

```bash
cd /path/to/clawjob
chmod +x deploy/verify-and-fix-until-pass.sh
./deploy/verify-and-fix-until-pass.sh
```

脚本会：运行验证 → 若失败则按错误类型 SSH 到服务器做修复（启动容器 / init_db / 配置 CORS）→ 再次验证，最多重复 5 次，直到 **All checks passed** 或无法自动修复。

---

## 仅验证（不自动修复）

```bash
python3 deploy/verify-deployed.py http://43.99.97.240:8000
```

结果会打印到终端并写入 `deploy/verify-result.txt`。若出现错误，可按下表排查。

## 错误与修复对照

| 现象 | 可能原因 | 修复方法 |
|------|----------|----------|
| 请求超时 (timed out) | 防火墙未放行或服务未启动 | 1) 阿里云轻量控制台 → 防火墙 → 放行 TCP 80、3000、8000<br>2) SSH 登录服务器执行 `docker ps`，确认 backend、frontend 为 Up；若未起则 `cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml up -d` |
| /health 返回 500 | 数据库未初始化或依赖服务不可用 | 在服务器上执行：<br>`cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c "from app.database.relational_db import init_db; init_db(); print(\"OK\")"'` |
| 后端启动即退出 (RuntimeError: JWT_SECRET / CORS_ORIGINS) | 生产校验未通过 | 在 `deploy/.env` 中设置：<br>• `JWT_SECRET` 为强随机字符串（非默认值）<br>• `CORS_ORIGINS` 为前端地址，如 `http://43.99.97.240:3000`（逗号分隔，禁止 `*`）<br>然后重启：`docker compose -f docker-compose.prod.yml up -d backend` |
| 前端请求 API 被 CORS 拒绝 | CORS_ORIGINS 未包含前端来源 | 在 `deploy/.env` 中设置 `CORS_ORIGINS=http://43.99.97.240:3000`（或你的前端域名），重启 backend |
| 注册/登录 401 或 422 | 请求体格式或 JWT 配置问题 | 确认 `deploy/.env` 中 `JWT_SECRET` 已设置；检查请求体是否包含 username/email/password（注册）、username/password（登录） |

## 在服务器上快速自检

SSH 登录后执行：

```bash
# 容器是否在跑
docker ps

# 后端健康（在服务器本机）
curl -s http://localhost:8000/health | head -c 500

# 若需重新初始化数据库
cd /opt/clawjob/deploy && docker compose -f docker-compose.prod.yml exec backend sh -c 'PYTHONPATH=. python3 -c "from app.database.relational_db import init_db; init_db(); print(\"OK\")"'
```

修复后再次运行验证脚本，直到全部通过。
