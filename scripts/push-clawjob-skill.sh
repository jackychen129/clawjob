#!/usr/bin/env bash
# 将主仓库 skills/clawjob/ 中的 SKILL.md、reference.md 同步到独立技能仓库并推送 GitHub。
# 用法（在 clawjob 仓库根目录）:
#   ./scripts/push-clawjob-skill.sh
# 可选环境变量:
#   CLAWJOB_SKILL_REMOTE   默认 https://github.com/jackychen129/clawjob-skill.git
#   CLAWJOB_SKILL_CLONE    克隆目录，默认 /tmp/clawjob-skill
#   SKIP_PUSH=1            仅复制并提交到本地克隆，不 push（用于检查 diff）

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${CLAWJOB_SKILL_REMOTE:-https://github.com/jackychen129/clawjob-skill.git}"
CLONE_DIR="${CLAWJOB_SKILL_CLONE:-/tmp/clawjob-skill}"
SRC="$REPO_ROOT/skills/clawjob"

for f in SKILL.md reference.md; do
  if [[ ! -f "$SRC/$f" ]]; then
    echo "错误: 缺少 $SRC/$f"
    exit 1
  fi
done

if [[ ! -d "$CLONE_DIR/.git" ]]; then
  echo ">>> 克隆 $REMOTE -> $CLONE_DIR"
  rm -rf "$CLONE_DIR"
  git clone "$REMOTE" "$CLONE_DIR"
else
  echo ">>> 拉取 $CLONE_DIR"
  git -C "$CLONE_DIR" fetch origin
  git -C "$CLONE_DIR" checkout main
  git -C "$CLONE_DIR" pull origin main
fi

mkdir -p "$CLONE_DIR/clawjob"
cp "$SRC/SKILL.md" "$CLONE_DIR/clawjob/SKILL.md"
cp "$SRC/reference.md" "$CLONE_DIR/clawjob/reference.md"

if git -C "$CLONE_DIR" diff --quiet && git -C "$CLONE_DIR" diff --cached --quiet; then
  echo ">>> clawjob-skill 无变更，跳过提交"
  exit 0
fi

MSG="sync: SKILL.md & reference.md from clawjob ($(date -u +%Y-%m-%d)"
if git -C "$REPO_ROOT" rev-parse --short HEAD >/dev/null 2>&1; then
  MSG="${MSG}, clawjob $(git -C "$REPO_ROOT" rev-parse --short HEAD))"
fi
MSG="${MSG})"

git -C "$CLONE_DIR" add clawjob/SKILL.md clawjob/reference.md
git -C "$CLONE_DIR" commit -m "$MSG" || {
  echo ">>> 提交失败（可能无变更或需配置 user.name/email）"
  exit 1
}

if [[ "${SKIP_PUSH:-}" == "1" ]]; then
  echo ">>> SKIP_PUSH=1，已提交到 $CLONE_DIR，未执行 push"
  exit 0
fi

echo ">>> 推送到 origin main"
git -C "$CLONE_DIR" push origin main
echo ">>> 完成: $REMOTE"
