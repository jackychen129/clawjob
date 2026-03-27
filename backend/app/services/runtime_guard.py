from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock
from urllib.parse import urlparse
from typing import Dict


class RuntimeCircuitGuard:
    def __init__(self, threshold: int = 3, open_seconds: int = 60):
        self.threshold = threshold
        self.open_seconds = open_seconds
        self._lock = Lock()
        self._state: Dict[str, dict] = {}

    def _host(self, url: str) -> str:
        h = urlparse(url).netloc or "unknown"
        return h.lower()

    def can_request(self, url: str) -> tuple[bool, str]:
        host = self._host(url)
        with self._lock:
            row = self._state.get(host)
            if not row:
                return True, "closed"
            open_until = row.get("open_until")
            if open_until and isinstance(open_until, datetime):
                if datetime.utcnow() < open_until:
                    return False, f"open_until:{open_until.isoformat()}Z"
                row["open_until"] = None
                row["state"] = "half_open"
            return True, row.get("state", "closed")

    def record_success(self, url: str) -> None:
        host = self._host(url)
        with self._lock:
            self._state[host] = {
                "state": "closed",
                "consecutive_failures": 0,
                "last_success_at": datetime.utcnow(),
                "open_until": None,
            }

    def record_failure(self, url: str) -> None:
        host = self._host(url)
        with self._lock:
            row = self._state.get(host) or {
                "state": "closed",
                "consecutive_failures": 0,
                "open_until": None,
            }
            row["consecutive_failures"] = int(row.get("consecutive_failures", 0)) + 1
            row["last_failure_at"] = datetime.utcnow()
            if row["consecutive_failures"] >= self.threshold:
                row["state"] = "open"
                row["open_until"] = datetime.utcnow() + timedelta(seconds=self.open_seconds)
            self._state[host] = row

    def snapshot(self) -> dict:
        with self._lock:
            items = []
            for host, st in self._state.items():
                items.append(
                    {
                        "host": host,
                        "state": st.get("state", "closed"),
                        "consecutive_failures": int(st.get("consecutive_failures", 0)),
                        "open_until": (st.get("open_until").isoformat() + "Z") if st.get("open_until") else None,
                        "last_failure_at": (st.get("last_failure_at").isoformat() + "Z") if st.get("last_failure_at") else None,
                        "last_success_at": (st.get("last_success_at").isoformat() + "Z") if st.get("last_success_at") else None,
                    }
                )
            return {"items": items, "threshold": self.threshold, "open_seconds": self.open_seconds}

    def set_state(self, host: str, state: str) -> None:
        host_key = (host or "").strip().lower()
        if not host_key:
            return
        with self._lock:
            row = self._state.get(host_key) or {
                "state": "closed",
                "consecutive_failures": 0,
                "open_until": None,
            }
            now = datetime.utcnow()
            if state == "open":
                row["state"] = "open"
                row["open_until"] = now + timedelta(seconds=self.open_seconds)
            elif state == "half_open":
                row["state"] = "half_open"
                row["open_until"] = None
            else:
                row["state"] = "closed"
                row["open_until"] = None
                row["consecutive_failures"] = 0
            self._state[host_key] = row

    def reset(self, host: str) -> None:
        host_key = (host or "").strip().lower()
        if not host_key:
            return
        with self._lock:
            if host_key in self._state:
                del self._state[host_key]

