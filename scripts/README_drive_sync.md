# Google Drive full sync (all business files)

WSL でリポ内の `PJ_asset_Data` が空のときは、先に [../docs/storage-coexistence.md](../docs/storage-coexistence.md) の「リンク切れ」節と `scripts/link_pj_asset_data.sh` でシンボリックリンクを合わせてください。

This setup syncs every file under your Drive folder to local disk:

- Non-Google files: downloaded as-is (`pdf`, `pptx`, `xlsx`, images, etc.)
- Google native files:
  - Sheets -> `.xlsx`
  - Docs -> `.docx`
  - Slides -> `.pptx`
  - Drawings -> `.pdf`
  - Unsupported native types -> `.url` shortcut

## 1) Install dependencies

```bash
cd /home/mg_ogawa/DevelopmentRoom/salse_consulting
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

## 2) Prepare OAuth credentials

1. Open Google Cloud Console.
2. Enable **Google Drive API**.
3. Create OAuth Client ID (Desktop app).
4. Download JSON and save to:

`/home/mg_ogawa/DevelopmentRoom/salse_consulting/.secrets/google-drive-credentials.json`

## 3) Run first sync (includes OAuth browser login)

```bash
cd /home/mg_ogawa/DevelopmentRoom/salse_consulting
source .venv/bin/activate
python scripts/sync_drive_full.py \
  --root-folder-id "144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/PJ_asset_Data"
```

The Folder ID above is the **workspace-standard Drive hub**（RAW と作成物の正本）。サブフォルダの切り方は [../docs/drive-data-hub.md](../docs/drive-data-hub.md) を参照。

### 架電 RAW（別フォルダ → `call_rec/`）

架電用 RAW の正本は **[Drive フォルダ](https://drive.google.com/drive/folders/1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe?usp=drive_link)**（Folder ID `1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe`）。ローカルへは次で同期します。

```bash
cd /home/mg_ogawa/DevelopmentRoom/salse_consulting
source .venv/bin/activate
bash scripts/run_sync_call_raw.sh
```

## 4) Schedule (every day 09:20-18:20 every 20 min)

Use Windows Task Scheduler to run WSL command.

### Trigger

- Daily: Every 1 day
- Start: 09:20
- Repeat task every: 20 minutes
- For a duration of: 9 hours

### Action

Program:

`C:\Windows\System32\wsl.exe`

Arguments:

```text
-d Ubuntu --cd /home/mg_ogawa/DevelopmentRoom/salse_consulting bash -lc "source .venv/bin/activate && python scripts/sync_drive_full.py --root-folder-id 144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2 --output-dir /home/mg_ogawa/DevelopmentRoom/salse_consulting/PJ_asset_Data"
```

## Notes

- 同じ同期をシェルからまとめて実行する場合: `scripts/run_sync_pj_asset_data.sh`（リポルートの `PJ_asset_Data` に出力）
- 架電 RAW の同期: `scripts/run_sync_call_raw.sh`（リポルートの `call_rec/` に出力。詳細は [../docs/drive-data-hub.md](../docs/drive-data-hub.md)）
- **`PJ_asset_Data` と `project_hangarr` / NextCRM の分担**（同じファイルを二重に溜めない）: [../docs/storage-coexistence.md](../docs/storage-coexistence.md)
- Keep `.secrets/` private. It is ignored by `.gitignore`.
- First run may take time depending on file volume.
- If a file is opened and locked by another app, that file may fail in that cycle and recover on next run.
