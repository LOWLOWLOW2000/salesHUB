# 07_automation — 自動化スクリプト

## セットアップ（初回のみ）

```bash
cd data_project/2026-04_peak-hub/07_automation
python3 -m venv .venv
.venv/bin/pip install playwright python-dotenv
.venv/bin/python -m playwright install chromium
cp .env.example .env
# .env は認証方式に応じて編集（下記）
```

## スクリプト一覧

| スクリプト | 用途 |
|---|---|
| `src/generate_intake_csv.py` | PJシート投入用CSV生成 |
| `src/zoom_recording_downloader.py` | Zoom Phone 録音一括ダウンロード |

---

## Zoom Phone 録音ダウンロード — 認証方式

SSO・Google・社内IdP の場合は **メール/パスワードは使えません**。次のいずれかを使います（**優先順: A > B > C > D**）。

### A（推奨）: 既存 Chrome に CDP で接続

普段使っている Chrome を **リモートデバッグ付き**で起動し、Zoom にログインした状態のまま、スクリプトが同じセッションに接続します。

**Windows（コマンドプロンプト / PowerShell）**

```bat
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**macOS**

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

**Linux（ネイティブ）**

```bash
google-chrome --remote-debugging-port=9222
```

`.env` に追加:

```env
ZOOM_CDP_URL=http://127.0.0.1:9222
```

**WSL2 から Windows の Chrome に接続する場合**

- Windows で上記のように Chrome を起動する
- WSL からは `127.0.0.1:9222` では届かないことが多いです。次のいずれかを試してください。
  - `ZOOM_CDP_URL=http://$(cat /etc/resolv.conf | awk '/nameserver/{print $2; exit}'):9222`（WindowsホストIP）
  - または Windows の `ipconfig` で表示されるイーサネットアダプタの IPv4 を指定: `http://192.168.x.x:9222`

### B（次点）: storage_state を一度保存して再利用

1. `.env` に `ZOOM_EMAIL` は**書かない**（または空にする）
2. 実行:

```bash
.venv/bin/python src/zoom_recording_downloader.py --save-auth
```

3. ブラウザで **SSO 含め Zoom にログイン**し、完了したらターミナルで Enter
4. デフォルトで `07_automation/zoom_auth.json` に保存されます（`--save-auth-path` で変更可）
5. 以降は `zoom_auth.json` があれば自動で読み込みます。別パスにしたい場合は `.env` で:

```env
ZOOM_STORAGE_STATE=/absolute/path/to/zoom_auth.json
```

セッション切れ時は `--save-auth` を再度実行してください。

### C（補助）: Cookie JSON

Playwright の `add_cookies` 用の JSON 配列（または `{"cookies":[...]}`）をファイルに保存し:

```env
ZOOM_COOKIES_FILE=/absolute/path/to/cookies.json
```

**注意**: ブラウザ拡張でエクスポートした Cookie には **HttpOnly が含まれない**ことが多く、Zoom では認証が通らない場合があります。そのときは **A または B** を使ってください。

### D（後方互換）: メール + パスワード

Zoom のメール/パスワードログインのみ有効な場合:

```env
ZOOM_EMAIL=...
ZOOM_PASSWORD=...
```

---

## Zoom 録音DL — 実行例

```bash
cd data_project/2026-04_peak-hub/07_automation
.venv/bin/python src/zoom_recording_downloader.py --dry-run
```

```bash
.venv/bin/python src/zoom_recording_downloader.py \
  --from 2026-04-01 \
  --to 2026-04-27
```

```bash
.venv/bin/python src/zoom_recording_downloader.py --headless \
  --from 2026-04-01 --to 2026-04-27
```

### 保存先

```
02_data_raw/zoom_recordings/
  <日付>/
    <日付>_<発信者>.mp3
    <日付>_<発信者>_transcript.vtt
```

ダウンロードは **Playwright の `context.request`** を使うため、ブラウザと同じ Cookie が自動で付きます。

---

## 注意事項

- **自社アカウントでアクセス権のある録音のみ**を対象にしてください
- `.env` / `zoom_auth.json` / Cookie JSON は **Git・Drive に載せない**（`.gitignore` 済み）
- 取得済みファイルはスキップされます（差分取得）
- Zoom の UI 変更で一覧が取れない場合は `--dry-run` で確認し、セレクタ調整が必要になることがあります

---

## トラブルシューティング

| 症状 | 対処 |
|---|---|
| `認証方法が設定されていません` | `.env` で `ZOOM_CDP_URL` / `zoom_auth.json` / `ZOOM_COOKIES_FILE` / メールログインのいずれかを設定 |
| CDP で接続できない | Chrome を **9222** で起動したか、ファイアウォール、WSL の場合はホスト IP を確認 |
| ダウンロードが 403 | セッション切れ。`--save-auth` 再実行または CDP で再ログイン |
| 録音が 0 件 | `--dry-run` で URL が出るか確認。UI 変更の可能性 |
