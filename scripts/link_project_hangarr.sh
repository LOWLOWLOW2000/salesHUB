#!/usr/bin/env bash
# Links repo-root project_hangarr -> your Google Drive folder
# (e.g. I:\マイドライブ\project_hangarr).
# Git ignores the symlink if listed in .gitignore; otherwise treat as local-only.
# Usage:
#   ./scripts/link_project_hangarr.sh "/absolute/path/to/project_hangarr-on-drive"
# Or:
#   export PROJECT_HANGARR_REALPATH="/absolute/path" && ./scripts/link_project_hangarr.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-${PROJECT_HANGARR_REALPATH:-}}"
if [[ -z "${TARGET}" ]]; then
  echo "Usage: $0 <absolute-path-to-Drive-project_hangarr-folder>" >&2
  echo "   or: PROJECT_HANGARR_REALPATH=<path> $0" >&2
  echo "WSL example: $0 \"/mnt/i/マイドライブ/project_hangarr\"" >&2
  exit 1
fi
if [[ ! -d "${TARGET}" ]]; then
  echo "Not a directory: ${TARGET}" >&2
  exit 1
fi
DEST="${ROOT}/project_hangarr"
if [[ -e "${DEST}" && ! -L "${DEST}" ]]; then
  echo "Refusing to replace: ${DEST} exists and is not a symlink (move/merge contents first)." >&2
  echo "See docs/project-hangarr.md" >&2
  exit 1
fi
rm -f "${DEST}"
ln -s "${TARGET}" "${DEST}"
echo "OK: ${DEST} -> ${TARGET}"
