#!/bin/bash
# NOTE: translated comment in English.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG="$SCRIPT_DIR/deploy-output.txt"
echo "=== $(date) ===" > "$LOG"
echo "PWD=$(pwd)" >> "$LOG"
echo "SERVER_IP from env: $SERVER_IP" >> "$LOG"
cd "$SCRIPT_DIR/../.." || exit 1
echo "Running deploy..." >> "$LOG"
bash run-deploy.sh >> "$LOG" 2>&1
echo "Exit: $?" >> "$LOG"
echo "=== end $(date) ===" >> "$LOG"
