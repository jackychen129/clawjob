"""
序列化 datetime 为前端可正确解析的 ISO 字符串。
无时区的 naive datetime 按 UTC 输出并追加 'Z'，避免前端按本地时间解析导致时间偏差（如差 8 小时）。
"""
from datetime import datetime
from typing import Optional


def iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """返回 ISO 字符串；naive 视为 UTC 并追加 'Z'，便于前端 new Date(iso) 后 toLocaleString 显示正确本地时间。"""
    if dt is None:
        return None
    if hasattr(dt, "isoformat"):
        s = dt.isoformat()
        # NOTE: translated comment in English.
        if dt.tzinfo is None and "Z" not in s and "+" not in s:
            return s + "Z"
        return s
    return str(dt)
