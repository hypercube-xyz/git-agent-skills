#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

if [[ -L "$DEST" ]]; then
  resolved="$(readlink -f "$DEST")"
  case "$resolved" in
    "$REPO"|"$REPO"/*)
      echo "error: $DEST is a symlink into this repository ($resolved)" >&2
      exit 1
      ;;
  esac
fi

mkdir -p "$DEST"

while IFS= read -r skill_file; do
  skill_dir="$(dirname "$skill_file")"
  name="$(basename "$skill_dir")"
  target="$DEST/$name"

  if [[ -e "$target" && ! -L "$target" ]]; then
    echo "error: refusing to replace non-symlink target $target" >&2
    exit 1
  fi

  ln -sfn "$skill_dir" "$target"
  echo "linked $name -> $skill_dir"
done < <(find "$REPO/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print | LC_ALL=C sort)
