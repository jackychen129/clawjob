#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${CLAWJOB_ROOT:-/Users/jacky/Documents/jasonproject/clawjob}"
cd "$ROOT_DIR" || exit 1
mkdir -p "$ROOT_DIR/logs"
python3 "$ROOT_DIR/tools/monitor_agent_growth.py" --check-only >> "$ROOT_DIR/logs/agent_growth.log" 2>&1
