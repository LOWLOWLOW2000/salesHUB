# Google Drive full sync (all business files)

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
  --root-folder-id "1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/IS_01_hangar"
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
-d Ubuntu --cd /home/mg_ogawa/DevelopmentRoom/salse_consulting bash -lc "source .venv/bin/activate && python scripts/sync_drive_full.py --root-folder-id 1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq --output-dir /home/mg_ogawa/DevelopmentRoom/salse_consulting/IS_01_hangar"
```

## Notes

- Keep `.secrets/` private. It is ignored by `.gitignore`.
- First run may take time depending on file volume.
- If a file is opened and locked by another app, that file may fail in that cycle and recover on next run.
