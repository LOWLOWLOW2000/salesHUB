#!/usr/bin/env bash
# Backs up a non-symlink project_hangarr/ then links repo-root project_hangarr -> Drive folder.
# Default target: /mnt/i/マイドライブ/project_hangarr (I:\マイドライブ\project_hangarr)
# Usage:
#   ./scripts/setup_project_hangarr_symlink.sh
#   ./scripts/setup_project_hangarr_symlink.sh "/mnt/i/マイドライブ（account）/project_hangarr"
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-/mnt/i/マイドライブ/project_hangarr}"
cd "$ROOT"
if [[ -e project_hangarr && ! -L project_hangarr ]]; then
  backup="project_hangarr.__backup__$(date +%Y%m%d_%H%M%S)"
  echo "Backing up existing directory -> ${backup}"
  mv project_hangarr "$backup"
fi
bash "$ROOT/scripts/link_project_hangarr.sh" "$TARGET"
