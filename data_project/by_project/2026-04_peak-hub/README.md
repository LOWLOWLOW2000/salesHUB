# PeakHUB PJ データ管理

- **PJ**: PeakHUB 営業代行
- **開始**: 2026-04
- **担当**: 小川

---

## Driveリンク（正本）

| 種別 | リンク | 備考 |
|---|---|---|
| PJシート | （URLを記入） | 架電リスト・ステータス管理の正本 |
| 架電結果スプシ | （URLを記入） | 日次更新（12時・18時・22時） |
| 日週月レポート | （URLを記入） | 提出版（クライアント共有） |
| 共有素材フォルダ | （URLを記入） | クライアント提供資料 |

---

## フォルダ構成

```
2026-04_peak-hub/
  00_meta/          # PJ定義・CSV仕様・リンク集
  01_docs/          # ガイドライン・トークスクリプト・MTG議事録
  02_data_raw/      # 取り込み原本（上書きしない）
    gdrive_export/  # Driveからエクスポートしたファイル
    sheets_export/  # スプシのCSVエクスポート
  03_data_processed/
    intake/         # 投入用CSV（PJシートに貼る前のデータ）
  04_outputs_client/
    reports/        # Driveに上げる提出版レポート
  05_outputs_internal/
    research/       # 社内向け調査成果物（クライアント非共有）
    slides/         # 社内向けスライド
  06_ops_logs/      # 日報・作業ログ・意思決定ログ
  07_automation/
    src/            # スクリプト
```

---

## Driveに置くもの（最小・これ以外は置かない）

- PJシート（正本）
- 架電結果スプシ（正本）
- 日週月レポート（提出版）
- 共有素材（クライアント提供・合意済みのもののみ）

**Driveに置かないもの**: スクリプト / `.env` / 調査メモ / 社内向け資料 / 分析ロジック / 途中版

---

## 投入用CSV の作り方

詳細仕様: `00_meta/csv_spec.md`

### スプシからTSVを貼り付けて生成する場合

```bash
# スプシの行を全選択してコピー → 標準入力に貼り付け
python 07_automation/src/generate_intake_csv.py \
  --source baseconnect \
  --output 03_data_processed/intake
```

### TSVファイルを指定する場合

```bash
python 07_automation/src/generate_intake_csv.py \
  --source baseconnect \
  --input 02_data_raw/sheets_export/2026-04-27_raw.tsv \
  --output 03_data_processed/intake
```

### PJシートへの貼り付け手順

1. `03_data_processed/intake/` の最新CSVを開く
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
- 発番履歴: `06_ops_logs/lead_id_log.md` に記録

---

## 運用ルール

- `02_data_raw/` は上書き禁止（原本固定）
- `03_data_processed/intake/` のCSVは**提出後もローカルに残す**（再現・差分確認用）
- `04_outputs_client/` に上げたものが「提出版」。Driveにコピーしたらファイル名末尾に `_提出済` を付ける
- `.env` / APIキー類は**絶対にこのフォルダ以外に置かない / Driveに上げない**
