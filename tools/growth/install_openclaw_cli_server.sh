#!/usr/bin/env bash
# 在 Linux 生产机安装 OpenClaw CLI（user-space，不改系统 Node，不跑 onboard/daemon）
# 用法（服务器）：
#   CLAWJOB_ROOT=/opt/clawjob ./tools/growth/install_openclaw_cli_server.sh
#   OPENCLAW_PREFIX=/opt/clawjob/.openclaw-cli ./tools/growth/install_openclaw_cli_server.sh
set -euo pipefail

ROOT_DIR="${CLAWJOB_ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
PREFIX="${OPENCLAW_PREFIX:-$ROOT_DIR/.openclaw-cli}"
VERSION="${OPENCLAW_VERSION:-latest}"

echo "Installing OpenClaw CLI → $PREFIX (version=$VERSION, no onboard)"
mkdir -p "$PREFIX" "$ROOT_DIR/bin"

curl -fsSL --proto '=https' --tlsv1.2 https://openclaw.ai/install-cli.sh \
  | bash -s -- --prefix "$PREFIX" --no-onboard --version "$VERSION"

ln -sfn "$PREFIX/bin/openclaw" "$ROOT_DIR/bin/openclaw"
if [[ -x "$PREFIX/bin/node" ]]; then
  ln -sfn "$PREFIX/bin/node" "$ROOT_DIR/bin/node"
fi

export PATH="$ROOT_DIR/bin:$PREFIX/bin:${PATH:-/usr/bin}"
echo "OK: $(command -v openclaw) → $($ROOT_DIR/bin/openclaw --version 2>/dev/null || true)"
echo
echo "Documented path: $PREFIX/bin/openclaw (symlink: $ROOT_DIR/bin/openclaw)"
echo "Feishu is NOT configured by this installer. See docs/GROWTH_ACQUISITION_PROGRAM.md § OpenClaw/Feishu."
echo "Cron PATH should include: $ROOT_DIR/bin:$PREFIX/bin"
