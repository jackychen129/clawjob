#!/usr/bin/env bash
# Exit 0 when agents_count_public >= target (default 200). For user cron / launchd.
set -euo pipefail

API="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
TARGET="${CLAWJOB_AGENT_TARGET:-200}"

count="$(curl -sS --fail "${API%/}/stats" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(int(d.get('agents_count_public') or d.get('agents_count') or 0))
")"

if [ "$count" -ge "$TARGET" ]; then
  echo "MILESTONE agents_count_public=${count} >= target=${TARGET}"
  exit 0
fi

echo "WAIT agents_count_public=${count} target=${TARGET} remaining=$((TARGET - count))"
exit 1
