#!/usr/bin/env bash
# 从 GitHub 安装并运行 ClawJob MCP Server（npm 未发布时的 fallback）
set -euo pipefail
CACHE="${CLAWJOB_MCP_CACHE:-$HOME/.cache/clawjob-mcp-server}"
REPO="${CLAWJOB_MCP_REPO:-https://github.com/jackychen129/clawjob.git}"
REF="${CLAWJOB_MCP_REF:-main}"
PKG_DIR="$CACHE/packages/clawjob-mcp"

if [[ ! -f "$PKG_DIR/index.js" ]]; then
  mkdir -p "$CACHE"
  rm -rf "$CACHE/repo"
  git clone --depth 1 --branch "$REF" "$REPO" "$CACHE/repo"
  mkdir -p "$(dirname "$PKG_DIR")"
  cp -R "$CACHE/repo/packages/clawjob-mcp" "$PKG_DIR"
  (cd "$PKG_DIR" && npm install --omit=dev --no-audit --no-fund 2>/dev/null || npm install --omit=dev)
fi

export CLAWJOB_API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"
exec node "$PKG_DIR/index.js"
