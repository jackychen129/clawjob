# Contributing

感谢参与 ClawJob。请遵循以下约定，便于 review 与 CI 通过。

## 开发环境

1. 克隆仓库并阅读根目录 [README.md](README.md) 中的本地运行说明。
2. 后端：`backend/`，Python 3.10+，依赖见 `requirements.txt`。
3. 前端：`frontend/`，Node 20+，使用 `npm ci` 安装依赖。

## 提交前检查

与 [.github/workflows/ci.yml](.github/workflows/ci.yml) 保持一致：

```bash
# 后端
cd backend
PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py tests/test_data_iteration_engine.py tests/test_community_public_filter.py -q

# 前端
cd frontend
npm ci
npm run test:run
npm run build
```

## Pull Request

- 一个 PR 聚焦一类改动（功能、修复或重构），说明动机与测试方式。
- 用户可见文案需同步 `frontend/src/locales/zh-CN.ts` 与 `en.ts`。
- API 行为变更需补充或更新 `backend/tests/` 对应用例。
- 不要提交密钥、`.env` 或生产环境地址。

## 文档

- 产品规格与实现对照：[docs/PRD.md](docs/PRD.md)
- 文档索引：[docs/README.md](docs/README.md)
- 部署与运维文档仅放在 `deploy/`，不写入根 README。

## 行为准则

请保持讨论就事论事、尊重他人。问题与缺陷请使用 GitHub Issues。
