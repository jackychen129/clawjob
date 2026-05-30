# Monitoring Minimum

目标：在不引入复杂基础设施的前提下，先保证线上具备最小可观测能力与告警入口。

## 监控项（最小集）

- 可用性：`GET /health` 必须返回 `status=healthy` 且 `service=clawjob-backend`
- API 基线：`GET /stats`、`GET /stats/roi-series?days=14` 返回结构正确
- 延迟阈值：上述接口单次响应耗时默认不超过 `2500ms`
- 错误态：任何 `4xx/5xx` 直接判定失败（`5xx` 单独提示）

## 实现

- 脚本：`tools/monitor_probe.py`
- CI 定时任务：`.github/workflows/monitor.yml`
  - 每 30 分钟执行一次（`cron: */30 * * * *`）
  - 也支持手动触发（`workflow_dispatch`）

## 本地运行

```bash
python3 tools/monitor_probe.py
CLAWJOB_API_URL=https://api.clawjob.com.cn CLAWJOB_MONITOR_MAX_MS=2500 python3 tools/monitor_probe.py
```

## 告警处理建议

- 任一 probe 失败：优先查看 GitHub Actions 日志中的失败接口与耗时。
- 若失败持续超过 2 次：
  - 执行 `python3 tools/verify_online_e2e.py` 做二次确认
  - 检查最近发布与回滚点，必要时按 `docs/RELEASE_CHECKLIST.md` 回滚
