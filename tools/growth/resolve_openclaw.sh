#!/usr/bin/env bash
# Resolve OpenClaw CLI path for Linux server / local Mac without requiring TCC.
# Prefer explicit OPENCLAW_BIN, then project-local installs, then PATH.
#
# Usage (source):
#   # shellcheck source=resolve_openclaw.sh
#   source "$(dirname "$0")/resolve_openclaw.sh"
#   resolve_openclaw_bin || exit 1
#   "$OPENCLAW_BIN" --version
#
# Env:
#   OPENCLAW_BIN     — absolute path to openclaw binary (wins)
#   CLAWJOB_ROOT     — project root (default: derived from this file)
#   OPENCLAW_PREFIX  — install-cli prefix (default: $CLAWJOB_ROOT/.openclaw-cli)

resolve_openclaw_bin() {
  local root prefix candidate
  root="${CLAWJOB_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  prefix="${OPENCLAW_PREFIX:-$root/.openclaw-cli}"

  if [[ -n "${OPENCLAW_BIN:-}" && -x "${OPENCLAW_BIN}" ]]; then
    return 0
  fi

  for candidate in \
    "$root/bin/openclaw" \
    "$prefix/bin/openclaw" \
    "/opt/clawjob/bin/openclaw" \
    "/opt/clawjob/.openclaw-cli/bin/openclaw"
  do
    if [[ -x "$candidate" ]]; then
      OPENCLAW_BIN="$candidate"
      # Ensure sibling node (install-cli puts node next to openclaw) is on PATH
      export PATH="$(dirname "$candidate"):${PATH:-/usr/bin}"
      return 0
    fi
  done

  if command -v openclaw >/dev/null 2>&1; then
    OPENCLAW_BIN="$(command -v openclaw)"
    return 0
  fi

  OPENCLAW_BIN=""
  return 1
}

# True if Feishu channel looks configured (env or config file; does not call network).
openclaw_feishu_configured() {
  if [[ -n "${FEISHU_APP_ID:-}" && -n "${FEISHU_APP_SECRET:-}" ]]; then
    return 0
  fi
  local cfg home state
  cfg="${OPENCLAW_CONFIG_PATH:-}"
  if [[ -z "$cfg" ]]; then
    state="${OPENCLAW_STATE_DIR:-}"
    home="${OPENCLAW_HOME:-$HOME}"
    if [[ -n "$state" ]]; then
      cfg="$state/openclaw.json"
    else
      cfg="$home/.openclaw/openclaw.json"
    fi
  fi
  [[ -f "$cfg" ]] || return 1
  # Prefer python for reliable JSON; fallback to grep for enabled+appId presence
  if command -v python3 >/dev/null 2>&1; then
    python3 - "$cfg" <<'PY'
import json, sys
path = sys.argv[1]
try:
    cfg = json.load(open(path, encoding="utf-8"))
except Exception:
    sys.exit(1)
feishu = (cfg.get("channels") or {}).get("feishu") or {}
if not feishu.get("enabled", False) and not feishu.get("appId"):
    # accounts form
    accts = feishu.get("accounts") or {}
    ok = False
    for a in accts.values() if isinstance(accts, dict) else []:
        if isinstance(a, dict) and a.get("appId") and a.get("appSecret"):
            ok = True
            break
    if not ok:
        sys.exit(1)
else:
    if not (feishu.get("appId") and feishu.get("appSecret")):
        accts = feishu.get("accounts") or {}
        ok = False
        for a in accts.values() if isinstance(accts, dict) else []:
            if isinstance(a, dict) and a.get("appId") and a.get("appSecret"):
                ok = True
                break
        if not ok and not feishu.get("enabled"):
            sys.exit(1)
        if not ok:
            sys.exit(1)
sys.exit(0)
PY
  else
    grep -q '"feishu"' "$cfg" 2>/dev/null && grep -q '"appId"' "$cfg" 2>/dev/null
  fi
}
