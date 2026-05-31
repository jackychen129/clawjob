#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$ROOT_DIR/logs"
cd "$ROOT_DIR/backend"
python3 scripts/audit_agents.py >> "$ROOT_DIR/logs/audit_agents.log" 2>&1
