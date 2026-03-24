# NOTE: translated comment in English.
# NOTE: translated comment in English.
if [ -z "$DEPLOY_SSH_KEY" ] || [ ! -f "${DEPLOY_SSH_KEY/#\~/$HOME}" ]; then
  for k in "$HOME/Downloads/newclawjobkey.pem" "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
    if [ -f "$k" ]; then
      export DEPLOY_SSH_KEY="$k"
      break
    fi
  done
fi
