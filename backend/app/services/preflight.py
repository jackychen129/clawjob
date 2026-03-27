from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
from typing import List, Literal, Optional

from fastapi import HTTPException


Severity = Literal["blocker", "warning"]
Status = Literal["pass", "fail", "warn"]


@dataclass
class PreflightCheck:
    name: str
    severity: Severity
    status: Status
    message: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "severity": self.severity,
            "status": self.status,
            "message": self.message,
        }


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here, *here.parents]:
        hb = p / "HEARTBEAT.md"
        if hb.exists():
            return p
        if (p / ".git").exists():
            return p
    return Path.cwd()


def _heartbeat_checks(root: Path) -> List[str]:
    hb = root / "HEARTBEAT.md"
    if not hb.exists():
        return []
    try:
        lines = hb.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []
    out: List[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("- [ ]") or s.startswith("- [x]") or s.startswith("- [X]"):
            item = s[5:].strip()
            if item:
                out.append(item)
    return out


def run_preflight(context: str, *, required_envs: Optional[List[str]] = None) -> dict:
    root = _find_repo_root()
    checks: List[PreflightCheck] = []
    req_envs = required_envs or _required_envs_by_context(context)

    # Basic runtime checks
    for key in req_envs:
        val = (os.getenv(key) or "").strip()
        if val:
            checks.append(PreflightCheck(f"env:{key}", "blocker", "pass", "Environment variable is set"))
        else:
            checks.append(PreflightCheck(f"env:{key}", "blocker", "fail", "Environment variable is required"))

    free_mb = (shutil.disk_usage(str(root)).free // (1024 * 1024))
    if free_mb >= 100:
        checks.append(PreflightCheck("disk_space", "warning", "pass", f"Free disk {free_mb}MB"))
    else:
        checks.append(PreflightCheck("disk_space", "warning", "warn", f"Low free disk: {free_mb}MB"))

    hb_items = _heartbeat_checks(root)
    require_hb = _require_heartbeat_by_context(context)
    if hb_items:
        checks.append(PreflightCheck("heartbeat_rules", "warning", "pass", f"Loaded {len(hb_items)} checklist items"))
    else:
        sev: Severity = "blocker" if require_hb else "warning"
        st: Status = "fail" if require_hb else "warn"
        msg = "HEARTBEAT.md checklist not found"
        checks.append(PreflightCheck("heartbeat_rules", sev, st, msg))

    failed_blockers = [c for c in checks if c.severity == "blocker" and c.status == "fail"]
    summary = {
        "context": context,
        "ok": len(failed_blockers) == 0,
        "checks": [c.to_dict() for c in checks],
        "failed_blockers": len(failed_blockers),
        "warnings": len([c for c in checks if c.status == "warn"]),
    }
    return summary


def enforce_preflight(context: str, *, required_envs: Optional[List[str]] = None) -> dict:
    summary = run_preflight(context, required_envs=required_envs)
    if not summary["ok"]:
        raise HTTPException(status_code=400, detail={"message": "Preflight check failed", "preflight": summary})
    return summary


def _required_envs_by_context(context: str) -> List[str]:
    c = (context or "").strip().lower()
    env_key = f"PREFLIGHT_REQUIRED_ENVS_{c.upper()}"
    raw = (os.getenv(env_key) or "").strip()
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def _require_heartbeat_by_context(context: str) -> bool:
    force_all = (os.getenv("PREFLIGHT_REQUIRE_HEARTBEAT", "").strip().lower() in ("1", "true", "yes", "on"))
    if force_all:
        return True
    c = (context or "").strip().lower()
    env_key = f"PREFLIGHT_REQUIRE_HEARTBEAT_{c.upper()}"
    return (os.getenv(env_key, "").strip().lower() in ("1", "true", "yes", "on"))

