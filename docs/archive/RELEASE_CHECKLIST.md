# Release Checklist

用于线上发布前后的最小检查，目标是“可重复、可回滚、可验证”。

## 1) 发布前

- 同步主分支：`git pull origin main`
- 本地通过：
  - `cd backend && PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py tests/test_data_iteration_engine.py -q --tb=no`
  - `cd frontend && npm run test:run && npm run build && npm run e2e`
- 记录本次发布 commit：`git rev-parse --short HEAD`

## 2) 服务器发布

- 登录服务器并进入部署目录（示例）：
  - `cd /opt/clawjob`
- 拉取代码：
  - `git fetch origin && git checkout main && git pull origin main`
- 重建并重启：
  - `cd deploy && docker compose -f docker-compose.prod.yml up -d --build`

## 3) 发布后验证

- API 冒烟：
  - `python3 tools/verify_online_e2e.py`
- 浏览器冒烟（可在 CI 或运维机执行）：
  - `cd frontend && npx playwright install chromium && npm run e2e`

## 4) 回滚预案

- 获取上一个稳定版本 commit/tag（建议每次发布打 tag）。
- 回滚到稳定版本并重启容器：
  - `git checkout <stable_commit_or_tag>`
  - `cd deploy && docker compose -f docker-compose.prod.yml up -d --build`
- 回滚后重复第 3 步验证。
