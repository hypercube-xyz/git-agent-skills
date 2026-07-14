#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
find "$REPO/skills" -mindepth 2 -maxdepth 2 -name SKILL.md -print \
  | sed "s|^$REPO/||" \
  | LC_ALL=C sort
