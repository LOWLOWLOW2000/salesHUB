# project_hangarr（旧 `data_project`）

案件横断の **軽量 raw**（CSV エクスポート・スクリプト入出力・`master/` スナップショット等）のルート名です。  
**重い実ファイル**の正本は `PJ_asset_Data` 側に置き、ここと二重にフル同期しないでください（[storage-coexistence.md](./storage-coexistence.md)）。

## 標準ツリー（目安）

- `projects/<PJ-slug>/raw/` … `sheets_export` など
- `projects/<PJ-slug>/meta/` … ADR・PJ固有の決定ログ
- `master/` … 全案件横断の export 出力（スクリプト次第）

## Drive（例: `I:\マイドライブ\project_hangarr`）と同調

リポジトリ直下の `project_hangarr` を **Drive 上のフォルダへのシンボリックリンク**にします。  
**単一ハブ**（[drive-data-hub.md](./drive-data-hub.md)）運用なら、ハブ直下の `02_pipeline_raw` など **実際に作ったサブフォルダの絶対パス**（WSL の `/mnt/i/...`）を渡してください。

**おすすめ（既に `project_hangarr` が普通のフォルダでも自動退避してからリンク）:**

```bash
# WSL でリポジトリルートへ cd してから（+x が無くても動く）
bash scripts/setup_project_hangarr_symlink.sh
```

**手動（退避済み、または初回で `project_hangarr` が無いとき）:**

```bash
bash scripts/link_project_hangarr.sh "/mnt/i/マイドライブ/project_hangarr"
```

**Windows の PowerShell から一発（WSL のパス固定）:**

```powershell
wsl -d Ubuntu -- bash /home/mg_ogawa/DevelopmentRoom/salse_consulting/scripts/setup_project_hangarr_symlink.sh
```

Explorer で `マイドライブ（tarou.work363@gmail.com）` のように **アカウント付き表示**になっている場合は、実際のフォルダ名に合わせて  
`/mnt/i/マイドライブ（tarou.work363@gmail.com）/project_hangarr` を渡してください（`setup_project_hangarr_symlink.sh` に第1引数で渡せます）。

**注意:** `link_project_hangarr.sh` 単体は、リポ直下に **通常ディレクトリ**の `project_hangarr` があると拒否します。迷ったら **`setup_project_hangarr_symlink.sh`** を使ってください。

## 移行: `data_project` → `project_hangarr`

```bash
git mv data_project project_hangarr
# Git 以外: mv data_project project_hangarr
```
