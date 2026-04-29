#!/usr/bin/env bash
# Symlink every skill in plugins/personal/skills into ~/.codex/skills.
# Idempotent — safe to re-run after adding new skills.

set -euo pipefail

SKILLS_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")/skills" && pwd)"
SKILLS_DST="${CODEX_SKILLS_DIR:-$HOME/.codex/skills}"

mkdir -p "$SKILLS_DST"

for skill in "$SKILLS_SRC"/*/; do
  [ -d "$skill" ] || continue
  name="$(basename "$skill")"
  ln -sfn "${skill%/}" "$SKILLS_DST/$name"
  echo "linked $SKILLS_DST/$name -> ${skill%/}"
done
