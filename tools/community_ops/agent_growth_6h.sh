#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT_DIR/logs"
python3 "$ROOT_DIR/tools/monitor_agent_growth.py" --check-only >> "$ROOT_DIR/logs/agent_growth.log" 2>&1
