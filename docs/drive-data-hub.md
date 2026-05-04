# Drive 3 本構成（A: 作業ハブ / B: 重い実体 / C: 架電RAW）

このワークスペースは **Drive を 3 本に分けて運用**します。役割を物理的に分けることで、1000PJ 規模でも同期と容量の重さがレイヤーごとに切り出されます（理由づけは [re-design-2026-05.md](./re-design-2026-05.md)）。

## 1. ルート一覧

| 入口（ローカル） | Drive 役割 | URL | Folder ID |
|------------------|-----------|-----|-----------|
| `project_hangarr` | **A: 人 + AI の作業ハブ**（軽量 raw・作成物） | https://drive.google.com/drive/folders/1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq?usp=drive_link | `1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq` |
| `PJ_asset_Data` | **B: 重い実体**（PDF / 録音 / 動画 / PPTX） | https://drive.google.com/drive/folders/144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2?usp=drive_link | `144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2` |
| `call_rec` | **C: 架電 RAW**（録音・リスト・export） | https://drive.google.com/drive/folders/1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe?usp=drive_link | `1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe` |

リポジトリ側は **Git に載せない**（`.gitignore`）かつ **シンボリックリンクで Drive 同期先を指す**運用です。

## 2. 推奨ディレクトリ構造（Drive 上で手動作成）

### 2.1 A: `project_hangarr`（作業ハブ）

```
A (Drive root) /
└── 2026/
    └── PJname_yyyymmdd/
        ├── pj_sheet/        スプシの CSV export
        ├── meta/            README / ADR / PROJECT.md
        └── generated/       HTML/CSS 下書き、AI 生成 MD、レポート前段階
```

### 2.2 B: `PJ_asset_Data`（重い実体）

```
B (Drive root) /
└── 2026/
    └── PJname_yyyymmdd/
        ├── materials/       PDF / PPTX / 画像
        ├── call_voice/      録音
        ├── videos/          動画
        ├── client_doc/      クライアント資料の重いやつ
        ├── talk_script/     （任意）
        └── team_doc/        （任意）
```

### 2.3 C: `call_rec`（架電 RAW）

C は既存運用に合わせ、**ハブ直下の構成は同期元に従う**（ID をルートに `sync_drive_full.py` でミラーするだけ）。命名・サブフォルダの統一は、解析側で `_analytics/` がカバーします。

### 2.4 命名規約（A/B/C 共通）

- `PJ スラッグ`: `PJname_yyyymmdd`（半角英数とアンダースコアのみ。`-` は使わない）
- 年シャード: `2026/`, `2027/` …（A と B は同じ規約。1 階層フラットで多数 PJ を並べない）

## 3. ローカルでのリンク（入口名を固定）

```bash
# A 用（作業ハブ）
bash scripts/setup_project_hangarr_symlink.sh "<A の WSL 絶対パス>"

# B 用（重い実体）
./scripts/link_pj_asset_data.sh "<B の WSL 絶対パス>"

# C 用（架電 RAW）は API 同期で取り込み（リンクは作らない運用）
bash scripts/run_sync_call_raw.sh
```

WSL から見える絶対パスの探し方の例（環境差あり）:

```bash
find /mnt/c/Users -maxdepth 6 -type d -name 'project_hangarr' 2>/dev/null
find /mnt/i -maxdepth 4 -type d -name 'project_hangarr' 2>/dev/null
```

## 4. Drive → ローカルのフル同期

`scripts/sync_drive_full.py` の **`--root-folder-id`** にそれぞれの Folder ID を指定し、**出力先**を入口名に合わせます。

```bash
# B: 重い実体 → PJ_asset_Data/
python scripts/sync_drive_full.py \
  --root-folder-id "144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/PJ_asset_Data"

# C: 架電 RAW → call_rec/
python scripts/sync_drive_full.py \
  --root-folder-id "1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe" \
  --output-dir "/home/mg_ogawa/DevelopmentRoom/salse_consulting/call_rec"

# A: 作業ハブは原則「Drive for Desktop で同期した実フォルダへシンボリックリンク」運用。
#    必要であれば API 経由のフル同期も可能（出力先は project_hangarr/ の実体ディレクトリ）。
```

ラッパー: `scripts/run_sync_pj_asset_data.sh`（B 用）/ `scripts/run_sync_call_raw.sh`（C 用）。  
A 用ラッパー（`scripts/run_sync_project_hangarr.sh`）は次フェーズで追加予定。

## 5. ローカル限定の解析倉庫 `_analytics/`

Drive A/B/C の **派生物** として、PJ 横串の KPI と AI 解析を `_analytics/` に置きます。**Drive には載せません**（再生成可能なため）。

- スキーマ: [_analytics-spec.md](./_analytics-spec.md)
- 音声 → 文字起こし: [voice-pipeline.md](./voice-pipeline.md)

## 6. 旧フォルダ ID からの切り替え

- 旧「単一ハブ」運用（`144hJUwro1nQ-...` を A/B/C 兼用にしようとしていた構成）からは、本ドキュメントの **3 本分離**へ切り替えます。
- A の `1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq` は元から「作業ハブ用途」を想定していた ID。サブフォルダ（`<year>/<pj_slug>/...`）を Drive 側で揃えてからリンクを張替えてください。
- 切替時は **Drive 側でファイルを動かしてからリンクを張る**順で進めると、二重化を最小化できます。
