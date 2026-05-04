#!/usr/bin/env bash
# Links repo-root PJ_asset_Data -> your real Drive folder (e.g. 00.IS_01_hangar). Git ignores the symlink.
# Usage:
#   ./scripts/link_pj_asset_data.sh "/absolute/path/to/your-drive-root-folder"
# Or:
#   export PJ_ASSET_REALPATH="/absolute/path/to/your-drive-root-folder" && ./scripts/link_pj_asset_data.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${1:-${PJ_ASSET_REALPATH:-}}"
if [[ -z "${TARGET}" ]]; then
  echo "Usage: $0 <absolute-path-to-drive-PJ-assets-folder>" >&2
  echo "   or: PJ_ASSET_REALPATH=<path> $0" >&2
  exit 1
fi
if [[ ! -d "${TARGET}" ]]; then
  echo "Not a directory: ${TARGET}" >&2
  exit 1
fi
rm -f "${ROOT}/PJ_asset_Data"
ln -s "${TARGET}" "${ROOT}/PJ_asset_Data"
echo "OK: ${ROOT}/PJ_asset_Data -> ${TARGET}"
