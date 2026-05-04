#!/usr/bin/env bash
# Syncs Google Drive folder for 架電 RAW (recordings, lists, exports) -> repo-root call_rec/
set -euo pipefail

ROOT_DIR="/home/mg_ogawa/DevelopmentRoom/salse_consulting"
cd "$ROOT_DIR"

source .venv/bin/activate

# 架電 RAW 正本（Drive）
CALL_RAW_FOLDER_ID="1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe"

python scripts/sync_drive_full.py \
  --root-folder-id "${CALL_RAW_FOLDER_ID}" \
  --output-dir "${ROOT_DIR}/call_rec"
