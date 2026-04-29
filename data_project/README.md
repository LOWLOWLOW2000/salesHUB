# data_project

全案件の架電 LOG・企業リストを集約するデータリポジトリ。
将来の SaaS 化時には `master/` の CSV を DB に移行することを想定。

---

## フォルダ構成

```
data_project/
├── master/                        ← 全案件統合データ（最終的にここが揃う状態）
│   ├── accounts/                  ← 全企業リスト（DB から export_master_data.py で生成）
│   │   └── all_accounts_YYYY-MM-DD.csv
│   └── call_logs/                 ← 全架電 LOG（同上）
│       └── all_call_logs_YYYY-MM-DD.csv
│
├── by_project/                    ← 案件ごとの raw / processed data
│   └── YYYY-MM_<pj-slug>/
│       ├── 00_meta/               # PJ定義・CSV仕様・リンク集
│       ├── 02_data_raw/           # 取り込み原本（上書きしない）
│       │   ├── sheets_export/     # スプシのCSVエクスポート
│       │   └── gdrive_export/     # Driveからエクスポートしたファイル
│       ├── 03_data_processed/
│       │   └── intake/            # PJシート投入用CSV（generate_intake_csv.py で生成）
│       └── 07_automation/
│           └── src/               # スクリプト
│
└── scripts/                       ← 共通スクリプト
    └── export_master_data.py      # DB → master/ CSV 一括エクスポート
```

---

## master/ の作り方

### 前提
- `salesHUB` が起動しており、PostgreSQL に接続できる状態
- `scripts/.env.local` に `DATABASE_URL` が設定されていること

```bash
# .env.local の例
DATABASE_URL=postgresql://user:pass@localhost:5432/saleshub_db
```

### エクスポート実行

```bash
cd data_project/scripts
pip install psycopg2-binary python-dotenv   # 初回のみ
python export_master_data.py
```

出力例:
```
[OK] 企業リスト: ../master/accounts/all_accounts_2026-04-28.csv (350件)
[OK] 架電LOG:   ../master/call_logs/all_call_logs_2026-04-28.csv (1200件)
```

---

## by_project/ の使い方

各 PJ フォルダの `README.md` を参照。

### 新規 PJ 追加手順
1. `by_project/YYYY-MM_<slug>/` フォルダを作成
2. `salesHUB` の Project レコードに `slug` フィールドを設定（同じ値にする）
3. `00_meta/csv_spec.md` に CSV 仕様を記述
4. `README.md` に Drive リンクを記録

---

## 運用ルール

| 場所 | 格納するもの |
|---|---|
| `master/accounts/` | 全案件の企業リスト（DB の SalesAccount テーブルと 1:1） |
| `master/call_logs/` | 全案件の架電 LOG（DB の CallLog テーブルと 1:1） |
| `by_project/<pj>/02_data_raw/` | 原本 CSV・スプシエクスポート（上書き禁止） |
| `by_project/<pj>/03_data_processed/intake/` | PJシート投入用 CSV |

- `master/` は **DB からの export が正本**。直接編集しない
- `by_project/` の `.env` / APIキー類は **絶対にここ以外に置かない・Drive に上げない**
- PDF・スライド等の資料は `IS_01_hangar/<pj-slug>/` に格納（このフォルダには置かない）
