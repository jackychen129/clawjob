#!/usr/bin/env python3
"""
生产主机深度探针：区分「端口开放但应用无响应」（实例卡死）与「服务正常」。

用法:
  python3 tools/production_host_probe.py
  PROBE_HOST=8.216.64.80 PROBE_API=https://api.clawjob.com.cn python3 tools/production_host_probe.py
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request

HOST = os.environ.get("PROBE_HOST", "8.216.64.80")
API = os.environ.get("PROBE_API", "https://api.clawjob.com.cn").rstrip("/")
PORTS = [int(p) for p in os.environ.get("PROBE_PORTS", "22,80,443").split(",") if p.strip()]
SSH_USER = os.environ.get("PROBE_SSH_USER", "root")
SSH_KEY = os.environ.get("PROBE_SSH_KEY", os.path.expanduser("~/Downloads/newclawjobkey.pem"))


def tcp_open(port: int, timeout: float = 4.0) -> bool:
    try:
        with socket.create_connection((HOST, port), timeout=timeout):
            return True
    except OSError:
        return False


def ssh_banner_ok(timeout: int = 12) -> bool:
    cmd = ["ssh"]
    if SSH_KEY and os.path.isfile(SSH_KEY):
        cmd.extend(["-i", SSH_KEY])
    cmd.extend(
        [
            "-o",
            "BatchMode=yes",
            "-o",
            f"ConnectTimeout={timeout}",
            "-o",
            "ConnectionAttempts=1",
            "-o",
            "StrictHostKeyChecking=accept-new",
            f"{SSH_USER}@{HOST}",
            "echo ok",
        ]
    )
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        return proc.returncode == 0 and "ok" in proc.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def api_ok(timeout: int = 15) -> tuple[bool, str]:
    url = f"{API}/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            if resp.status < 400 and body.get("status") == "healthy":
                return True, f"HTTP {resp.status}"
            return False, f"unexpected body: {body!r}"
    except urllib.error.URLError as e:
        return False, str(e)


def main() -> int:
    print(f"Host probe: {HOST} API={API}")
    port_state = {p: tcp_open(p) for p in PORTS}
    print("TCP:", " ".join(f"{p}:{'open' if port_state.get(p) else 'closed'}" for p in PORTS))

    ssh_ok = ssh_banner_ok()
    http_ok, http_detail = api_ok()
    print(f"SSH banner: {'OK' if ssh_ok else 'FAIL'}")
    print(f"HTTPS API:  {'OK' if http_ok else 'FAIL'} ({http_detail})")

    all_ports_open = all(port_state.get(p) for p in PORTS if p in (22, 80, 443))
    if all_ports_open and (not ssh_ok or not http_ok):
        print(
            "\nHUNG: ports accept connections but sshd/HTTP unresponsive — reboot ECS in Aliyun console.",
            file=sys.stderr,
        )
        return 3
    if not http_ok:
        return 2
    if not ssh_ok:
        print("WARN: API healthy but SSH failed (deploy may need console/VNC)", file=sys.stderr)
        return 1
    print("Host probe passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
