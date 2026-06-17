#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${CLAWJOB_ROOT:-/Users/jacky/Documents/jasonproject/clawjob}"
cd "$ROOT_DIR/backend" || exit 1
mkdir -p "$ROOT_DIR/logs"
python3 scripts/audit_agents.py >> "$ROOT_DIR/logs/audit_agents.log" 2>&1
