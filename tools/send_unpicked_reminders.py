#!/usr/bin/env python3
"""定时任务：扫描发布超过 24h 仍无人接取的任务，给发布方发送站内提醒信。

对应后端接口：POST /tasks/send-unpicked-reminders（需登录态，建议用平台运营/超管账号的 token）。
满足 Roadmap Guardrail「无人接取任务 24h 内自动提醒」。

用法（crontab 每小时一次）：
  export CLAWJOB_API_URL=https://api.clawjob.com.cn
  export CLAWJOB_ACCESS_TOKEN=<运营账号 JWT>
  python3 tools/send_unpicked_reminders.py            # 实际发送
  python3 tools/send_unpicked_reminders.py --dry-run  # 仅预览待提醒任务，不写库

crontab 示例（每小时第 5 分钟执行，日志追加到 /var/log/clawjob-reminders.log）：
  5 * * * * CLAWJOB_API_URL=https://api.clawjob.com.cn CLAWJOB_ACCESS_TOKEN=xxx \
            /usr/bin/python3 /opt/clawjob/tools/send_unpicked_reminders.py >> /var/log/clawjob-reminders.log 2>&1

退出码：0 成功；2 缺少 token；3 请求失败。
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def main() -> int:
    base = (env("CLAWJOB_API_URL") or "http://localhost:8000").rstrip("/")
    token = env("CLAWJOB_ACCESS_TOKEN")
    dry_run = "--dry-run" in sys.argv[1:]

    if not token:
        print("ERROR: 缺少 CLAWJOB_ACCESS_TOKEN（请设置运营/超管账号 JWT）", file=sys.stderr)
        return 2

    url = f"{base}/tasks/send-unpicked-reminders" + ("?dry_run=true" if dry_run else "")
    req = urllib.request.Request(
        url,
        data=b"{}",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    ts = datetime.now(timezone.utc).isoformat()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(f"[{ts}] HTTP {e.code} 调用失败: {body}", file=sys.stderr)
        return 3
    except Exception as e:  # noqa: BLE001
        print(f"[{ts}] 请求错误: {e}", file=sys.stderr)
        return 3

    reminded = out.get("reminded") or out.get("reminded_task_ids") or []
    skipped = out.get("skipped") or out.get("skipped_task_ids") or []
    mode = "dry-run" if dry_run else "sent"
    print(
        f"[{ts}] {mode}: reminded={len(reminded)} skipped={len(skipped)} "
        f"reminded_ids={reminded} ",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
