#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="/home/mg_ogawa/DevelopmentRoom/salse_consulting"
cd "$ROOT_DIR"

source .venv/bin/activate

python scripts/sync_drive_full.py \
  --root-folder-id "1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/IS_01_hangar"

