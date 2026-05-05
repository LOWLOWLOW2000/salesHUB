# PeakHUB PJ データ管理（人間向け）

- **PJ**: PeakHUB 営業代行
- **開始**: 2026-04
- **担当**: 小川

このフォルダ（`data_project/projects/2026-04_peak-hub/`）**だけ開けば**、メタ・原本・生成物・成果物・スクリプトまで一通り触れます。slug や正本の一行まとめは **[PROJECT.md](./PROJECT.md)**。

---

## フォルダの地図

| パス | 役割 |
|---|---|
| `meta/` | CSV 仕様・マニフェスト仕様・ADR・リンク（詳細仕様はここ） |
| `raw/` | 取り込み原本。**上書きしない**（スプシ export、`zoom_recordings` など） |
| `derived/` | 生成物（`intake/` の投入用 CSV、`asset_manifest.csv`） |
| `deliver/client/` | クライアント提出に関わる成果物（例: `reports/`） |
| `deliver/internal/` | 社内向け（調査・スライドなど） |
| `notes/` | 運用ログ・メモ（例: `lead_id_log.md` を置く想定） |
| `tools/` | この PJ 専用 Python・`.env`・実行手順は `tools/README.md` |

---

## Driveリンク（正本）

| 種別 | リンク | 備考 |
|---|---|---|
| Drive root（資料ストレージ） | `https://drive.google.com/drive/folders/1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq?usp=drive_link` | `PJ_asset_Data` の正本（配下に PJ フォルダを作って運用） |
| PJシート | （URLを記入） | 架電リスト・ステータス管理の正本 |
| 架電結果スプシ | （URLを記入） | 日次更新（12時・18時・22時） |
| 日週月レポート | （URLを記入） | 提出版（クライアント共有） |
| 共有素材フォルダ | （URLを記入） | クライアント提供資料 |

---

## 日常の流れ（ざっくり）

1. スプシから TSV/CSV を export → `raw/sheets_export/` などに保存（日付付き推奨）
2. 必要なら `tools/src/generate_intake_csv.py` で `derived/intake/` に投入用 CSV を生成
3. PJシートへ貼り付け（手順は下記）
4. 提出物は `deliver/client/` を経由し、Drive の正本へ（ルールどおり）

---

## PJシートのRAWをローカルで見る（スナップショット）

Drive上のPJシート（正本）をローカルに **XLSX/CSVとしてスナップショット保存**し、CursorからRAW確認したいとき。

出力先: `raw/gdrive_export/`

```bash
cd data_project/projects/2026-04_peak-hub/tools
.venv/bin/pip install -r requirements.txt
.venv/bin/python src/export_pj_sheet_snapshot.py \
  --spreadsheet-id "<SPREADSHEET_ID>" \
  --sheet-name "<TAB_NAME>"
```

初回はブラウザログイン（OAuth）が走ります（認証情報はリポルートの `.secrets/` を利用）。

---

## Driveに置くもの（最小・これ以外は置かない）

- PJシート（正本）
- 架電結果スプシ（正本）
- 日週月レポート（提出版）
- 共有素材（クライアント提供・合意済みのもののみ）

**Driveに置かないもの**: スクリプト / `.env` / 調査メモ / 社内向け資料 / 分析ロジック / 途中版

---

## 投入用CSV の作り方

詳細仕様: **`meta/csv_spec.md`**

### スプシからTSVを貼り付けて生成する場合

```bash
cd data_project/projects/2026-04_peak-hub/tools
# スプシの行を全選択してコピー → 標準入力に貼り付け
.venv/bin/python src/generate_intake_csv.py --source baseconnect
```

### TSVファイルを指定する場合

```bash
cd data_project/projects/2026-04_peak-hub/tools
.venv/bin/python src/generate_intake_csv.py \
  --source baseconnect \
  --input ../raw/sheets_export/2026-04-27_raw.tsv
```

### PJシートへの貼り付け手順

1. `derived/intake/` の最新CSVを開く
2. `電話番号` 列のセル書式を**書式なしテキスト**に変更（先頭`0`落ち防止）
3. CSVの**2行目以降**を全選択してコピー
4. PJシートの **A2セル** を選択
5. **「形式を選択して貼り付け」→「値のみ」** で貼り付け
6. E列（`_ignore`）は上書きしても空なので問題なし
7. CR列以降（架電回数〜）は**触らない**（関数列）

---

## lead_id 発番ルール

- 形式: `PEAK-000001`（6桁ゼロ埋め）
- **一度発番したら変更しない**
- 重複チェックキー: `電話番号`（正規化後） or `企業名+都道府県`
- 発番履歴: `notes/lead_id_log.md` に記録（ファイルがなければ作成）

---

## 運用ルール

- `raw/` は上書き禁止（原本固定）
- `derived/intake/` のCSVは**提出後もローカルに残す**（再現・差分確認用）
- `deliver/client/` に上げたものが「提出版」。Driveにコピーしたらファイル名末尾に `_提出済` を付ける
- `.env` / APIキー類は**この PJ の `tools/` 以外に置かない / Driveに上げない**

---

## トラブル時の最初の一手

- **`PJ_asset_Data` が空・リンク切れ（WSL）**: リポルートの `scripts/link_pj_asset_data.sh` と [docs/storage-coexistence.md](../../../docs/storage-coexistence.md)
- **Zoom 録音 DL**: `tools/README.md` の認証セクション
