# 在 source .deploy_env 之后、使用 SSH 之前 source 本文件。
# 当 DEPLOY_SSH_KEY 未设置或为空时，按顺序尝试常见密钥路径，找到第一个存在的即设置 DEPLOY_SSH_KEY。
if [ -z "$DEPLOY_SSH_KEY" ] || [ ! -f "${DEPLOY_SSH_KEY/#\~/$HOME}" ]; then
  for k in "$HOME/Downloads/newclawjobkey.pem" "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
    if [ -f "$k" ]; then
      export DEPLOY_SSH_KEY="$k"
      break
    fi
  done
fi
