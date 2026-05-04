#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/mg_ogawa/DevelopmentRoom/salse_consulting"
cd "$ROOT_DIR"

source .venv/bin/activate

python scripts/sync_drive_full.py \
  --root-folder-id "144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/PJ_asset_Data"
