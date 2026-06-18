#!/bin/bash
# 生产环境恢复：诊断 →（可选）阿里云重启 → 等待 SSH → 部署 → 验证
#
# 典型场景：TCP 22/80/443 可连，但 SSH banner / HTTPS 超时（实例卡死）。
#
# 用法:
#   ./deploy/recover-production.sh              # 诊断 + 若 SSH 可用则部署
#   ./deploy/recover-production.sh --reboot     # 尝试 aliyun 重启后部署（需有效 AK + INSTANCE_ID）
#   ./deploy/recover-production.sh --deploy-only # 跳过诊断/重启，直接部署
#
# 若本机 aliyun Access Key 已禁用，请先在控制台手动重启实例：
#   https://ecs.console.aliyun.com → 公网 IP 8.216.64.80 → 重启

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ -f "$SCRIPT_DIR/.deploy_env" ]; then
  set -a
  # shellcheck source=/dev/null
  . "$SCRIPT_DIR/.deploy_env"
  set +a
fi
# shellcheck source=/dev/null
[ -f "$SCRIPT_DIR/ssh_key_fallback.sh" ] && . "$SCRIPT_DIR/ssh_key_fallback.sh"

SERVER_IP="${SERVER_IP:-}"
SSH_USER="${SSH_USER:-root}"
SITE_DOMAIN="${SITE_DOMAIN:-clawjob.com.cn}"
SSL_DOMAIN="${SSL_DOMAIN:-$SITE_DOMAIN}"
API_URL="https://api.${SITE_DOMAIN}"
APP_URL="https://app.${SITE_DOMAIN}"
REGION="${ALIBABA_CLOUD_REGION:-ap-southeast-1}"
INSTANCE_ID="${ALIBABA_CLOUD_ECS_INSTANCE_ID:-}"

DO_REBOOT=0
DEPLOY_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --reboot) DO_REBOOT=1 ;;
    --deploy-only) DEPLOY_ONLY=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"
      exit 0
      ;;
    *)
      echo "未知参数: $arg（可用 --reboot / --deploy-only）"
      exit 1
      ;;
  esac
done

if [ -z "$SERVER_IP" ]; then
  echo "错误：请在 deploy/.deploy_env 中设置 SERVER_IP"
  exit 1
fi

KEY="${DEPLOY_SSH_KEY/#\~/$HOME}"
if [ -n "${DEPLOY_SSH_KEY:-}" ] && [ -f "$KEY" ]; then
  SSH_BASE=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=12)
else
  SSH_BASE=(ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=12)
fi
SSH_TARGET="${SSH_USER}@${SERVER_IP}"

port_open() {
  nc -z -w 4 "$SERVER_IP" "$1" >/dev/null 2>&1
}

ssh_ok() {
  "${SSH_BASE[@]}" -o BatchMode=yes -o ConnectionAttempts=1 "$SSH_TARGET" "echo ok" >/dev/null 2>&1
}

http_ok() {
  curl -fsS -m 12 "$API_URL/health" >/dev/null 2>&1
}

diagnose() {
  echo "========== 生产诊断 (${SERVER_IP} / ${SITE_DOMAIN}) =========="
  local p22 p80 p443 hung=0
  port_open 22 && p22=1 || p22=0
  port_open 80 && p80=1 || p80=0
  port_open 443 && p443=1 || p443=0
  echo "TCP 22/80/443: ${p22}/${p80}/${p443}"

  if [ "$p22" = 1 ] && ! ssh_ok; then
    echo "SSH: 端口开放但 banner 交换失败 → 实例可能卡死（sshd 无响应）"
    hung=1
  elif ssh_ok; then
    echo "SSH: 正常"
  else
    echo "SSH: 不可达"
    hung=1
  fi

  if curl -fsS -m 12 "$API_URL/health" >/dev/null 2>&1; then
    echo "HTTPS API: 正常 (${API_URL})"
  else
    echo "HTTPS API: 超时或失败 (${API_URL})"
    [ "$p443" = 1 ] && hung=1
  fi
  echo ""

  if [ "$hung" = 1 ]; then
    echo ">>> 判定：应用层无响应。请在阿里云 ECS 控制台对公网 IP ${SERVER_IP} 的实例执行「重启」或「强制重启」。"
    echo ">>> 控制台: https://ecs.console.aliyun.com"
    echo ">>> 若需 CLI 重启：在 RAM 控制台启用 Access Key，并设置 ALIBABA_CLOUD_ECS_INSTANCE_ID 后执行:"
    echo ">>>   ./deploy/aliyun-reboot-ecs.sh"
    echo ""
    return 2
  fi
  return 0
}

try_aliyun_reboot() {
  if ! command -v aliyun >/dev/null 2>&1; then
    echo "未安装 aliyun CLI，跳过 API 重启"
    return 1
  fi
  if [ -z "$INSTANCE_ID" ]; then
    echo "未设置 ALIBABA_CLOUD_ECS_INSTANCE_ID，尝试按公网 IP 查找实例..."
    INSTANCE_ID="$("$SCRIPT_DIR/aliyun-reboot-ecs.sh" --find-only 2>/dev/null | tail -1 || true)"
    if [[ ! "$INSTANCE_ID" =~ ^i- ]]; then
      echo "无法解析实例 ID。请在 deploy/.deploy_env 添加 ALIBABA_CLOUD_ECS_INSTANCE_ID=i-xxx"
      return 1
    fi
    echo "找到实例: $INSTANCE_ID"
  fi
  echo ">>> 调用 aliyun RebootInstance (${REGION} ${INSTANCE_ID})..."
  if aliyun ecs RebootInstance --RegionId "$REGION" --InstanceId "$INSTANCE_ID" --ForceStop true; then
    echo "重启指令已发送，等待实例恢复（约 2–4 分钟）..."
    return 0
  fi
  echo "aliyun 重启失败（常见原因：Access Key 被禁用）。请改用手动控制台重启。"
  return 1
}

wait_for_ssh() {
  local max="${WAIT_SSH_SECONDS:-300}" elapsed=0 step=10
  echo ">>> 等待 SSH 就绪（最多 ${max}s）..."
  while [ "$elapsed" -lt "$max" ]; do
    if ssh_ok; then
      echo "SSH 已恢复 (${elapsed}s)"
      return 0
    fi
    sleep "$step"
    elapsed=$((elapsed + step))
    echo "  ... ${elapsed}s"
  done
  echo "超时：SSH 仍未恢复"
  return 1
}

run_deploy() {
  echo "========== 部署主应用 =========="
  FORCE_REBUILD_FRONTEND=1 bash "$SCRIPT_DIR/deploy-to-server.sh"

  if [ -d "$(dirname "$REPO_ROOT")/clawjob-website" ]; then
    echo ""
    echo "========== 部署官网 =========="
    SSL_DOMAIN="$SSL_DOMAIN" \
      VITE_TASK_HALL_URL="$APP_URL" \
      VITE_STATS_API_URL="$API_URL" \
      bash "$SCRIPT_DIR/deploy-website-only.sh"
  else
    echo "（跳过官网：未找到同级 clawjob-website 目录）"
  fi

  echo ""
  echo "========== 线上验证 =========="
  python3 "$SCRIPT_DIR/verify-deployed.py" "$API_URL"
  python3 "$REPO_ROOT/tools/monitor_probe.py" || true
}

# --- main ---
if [ "$DEPLOY_ONLY" = 0 ]; then
  set +e
  diagnose
  diag_rc=$?
  set -e
  if [ "$diag_rc" = 2 ]; then
    if [ "$DO_REBOOT" = 1 ]; then
      if ! try_aliyun_reboot; then
        echo ""
        echo "无法通过 API 重启。请登录阿里云控制台手动重启，然后执行:"
        echo "  ./deploy/recover-production.sh --deploy-only"
        exit 1
      fi
      wait_for_ssh || exit 1
    else
      echo "修复步骤："
      echo "  1) 阿里云控制台重启实例（公网 IP ${SERVER_IP}）"
      echo "  2) 重启完成后执行: ./deploy/recover-production.sh --deploy-only"
      echo "  或一步: ./deploy/recover-production.sh --reboot（需有效 aliyun AK + INSTANCE_ID）"
      exit 1
    fi
  fi
fi

if ! ssh_ok; then
  if [ "$DO_REBOOT" = 1 ]; then
    if ! try_aliyun_reboot; then
      echo "无法通过 API 重启。请手动控制台重启后执行 --deploy-only"
      exit 1
    fi
  else
    echo "SSH 不可用。请先重启实例，或加 --reboot（需有效 aliyun AK）"
    exit 1
  fi
  wait_for_ssh || {
    echo "仍无法 SSH。请确认实例已在控制台重启完成。"
    exit 1
  }
fi

run_deploy
echo ""
echo "========== 生产恢复完成 =========="
echo "  官网: https://${SITE_DOMAIN}"
echo "  应用: ${APP_URL}"
echo "  API:  ${API_URL}"
