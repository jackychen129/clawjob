#!/usr/bin/env bash
set -euo pipefail

# 一键发布前验证：
# 1) backend pytest
# 2) frontend vitest + build + playwright e2e
# 3) 线上监控探针（可通过 CLAWJOB_API_URL 覆盖）
#
# 用法：
#   ./tools/release_verify.sh
#   CLAWJOB_API_URL=https://api.clawjob.com.cn ./tools/release_verify.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
API_URL="${CLAWJOB_API_URL:-https://api.clawjob.com.cn}"

echo "[release-verify] root: ${ROOT_DIR}"
echo "[release-verify] api : ${API_URL}"

echo "[1/4] Backend tests"
(
  cd "${ROOT_DIR}/backend"
  PYTHONPATH=. python3 -m pytest tests/test_clawjob_api.py tests/test_data_iteration_engine.py -q --tb=no
)

echo "[2/4] Frontend unit tests"
(
  cd "${ROOT_DIR}/frontend"
  npm run test:run
)

echo "[3/4] Frontend build + e2e"
(
  cd "${ROOT_DIR}/frontend"
  npm run build
  npm run e2e
)

echo "[4/4] Production monitor probe"
(
  cd "${ROOT_DIR}"
  CLAWJOB_API_URL="${API_URL}" python3 tools/monitor_probe.py
)

SHORT_SHA="$(cd "${ROOT_DIR}" && git rev-parse --short HEAD)"
echo "[release-verify] all checks passed for commit ${SHORT_SHA}"
