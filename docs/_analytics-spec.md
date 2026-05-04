# `_analytics/` スキーマ仕様

ローカル限定の解析倉庫 `_analytics/` の **ファイル配置・命名・スキーマ**を固定するためのドキュメントです。  
ここが揺れると `cross_pj_kpi.csv` の横串が崩れるので、**キーを増減するときは必ずこのファイルを更新**してください。

## 1. 配置（必須）

```
_analytics/
├── by-pj/
│   └── <year>/<pj_slug>/
│       ├── metrics.json
│       ├── transcripts/<yyyymmdd>_<short>.md
│       ├── scripts/<script_id>.md
│       └── notes/<yyyymmdd>_<topic>.md
├── master/
│   ├── cross_pj_kpi.csv
│   ├── kpi_by_month.csv
│   └── insights/<yyyy>Q<n>_<topic>.md
└── manifest/catalog.csv
```

- `<year>` は 4 桁。`<pj_slug>` は `PJname_yyyymmdd`（半角英数とアンダースコア）。
- `_analytics/` 配下は **派生物**。手書きの一次情報は **`by-pj/.../{transcripts,scripts,notes}/*.md` と `metrics.json`** にだけ置く。
- `master/` は `scripts/build_master_kpi.py` の出力で、**全消し再生成可能**。

## 2. `metrics.json` スキーマ

PJ 1 つ × 期間（月）1 つの数値 KPI を 1 ファイルに格納します。配列にせず、**期間別のキー**で持ちます（`build_master_kpi.py` が縦に展開）。

```json
{
  "schema_version": "1.0",
  "pj_slug": "PJname_yyyymmdd",
  "year": 2026,
  "periods": {
    "2026-04": {
      "call_count": 412,
      "connect": 87,
      "appoint": 12,
      "uketsuke_ng": 95,
      "keyman_ng": 47,
      "shiryou_soufu": 18,
      "call_minutes": 880,
      "work_minutes": 1980,
      "scripts_used": ["pkh_v3", "pkh_v3_keyman"],
      "memo": null
    },
    "2026-05": {
      "call_count": null,
      "connect": null,
      "appoint": null,
      "uketsuke_ng": null,
      "keyman_ng": null,
      "shiryou_soufu": null,
      "call_minutes": null,
      "work_minutes": null,
      "scripts_used": [],
      "memo": null
    }
  }
}
```

### 2.1 必須キー（数値はすべて `int` または `null`）

| キー | 意味 | 単位 |
|------|------|------|
| `schema_version` | スキーマ版数（後方互換用） | 文字列 |
| `pj_slug` | PJ スラッグ（フォルダ名と一致） | 文字列 |
| `year` | 集計年 | 整数 |
| `periods.<yyyy-mm>.call_count` | 月の架電件数 | 件 |
| `periods.<yyyy-mm>.connect` | 通電（接続）件数 | 件 |
| `periods.<yyyy-mm>.appoint` | アポ獲得件数 | 件 |
| `periods.<yyyy-mm>.uketsuke_ng` | 受付 NG 件数 | 件 |
| `periods.<yyyy-mm>.keyman_ng` | キーマン NG 件数 | 件 |
| `periods.<yyyy-mm>.shiryou_soufu` | 資料送付件数 | 件 |
| `periods.<yyyy-mm>.call_minutes` | 架電時間合計 | 分 |
| `periods.<yyyy-mm>.work_minutes` | 稼働時間合計 | 分 |
| `periods.<yyyy-mm>.scripts_used` | 使ったスクリプト ID 配列 | 文字列配列 |
| `periods.<yyyy-mm>.memo` | 自由記述（短く） | 文字列 or `null` |

### 2.2 拡張ルール

- **追加可能**: 新しい数値キーは「`int` または `null` のみ」「単位は名前で明示」。例: `connect_minutes`, `meeting_count`。
- **追加禁止**: 文章を `memo` 以外に入れない（解析しづらいため）。長文は MD に置き、`metrics.json` には **数値**だけ。
- **削除する場合**: `schema_version` を上げる。古い PJ を読む側は欠損キーを `null` 扱いで吸収する。

## 3. MD frontmatter スキーマ

`by-pj/.../transcripts/*.md` `scripts/*.md` `notes/*.md` の **先頭**に YAML を必須で書きます。本文は自由記述で OK。

```markdown
---
type: transcript          # transcript | script | note | insight
pj_slug: PJname_yyyymmdd
date: 2026-04-15
period: 2026-04           # 集計帰属の年月（PJ slug 末尾の日付と別）
script_id: pkh_v3         # type=script のときだけ必須
call_count: 28            # type=transcript|script のときに任意
connect: 6
appoint: 1
uketsuke_ng: 5
keyman_ng: 8
shiryou_soufu: 2
outcome: 資料送付         # 文字列。固定語彙は付録 A
tags: [SaaS, 新規, 製造業]
source_md_path: null      # type=insight 以外は null（自分自身を指す）
sources: []               # type=insight のとき、参照した CSV/MD のパス配列
created: 2026-05-04
---
# 本文（自由記述）
```

### 3.1 type 別の必須キー

| type | 必須 | 任意 |
|------|------|------|
| `transcript` | `pj_slug` `date` `period` | `call_count` 系 KPI、`tags` |
| `script` | `pj_slug` `date` `period` `script_id` | `call_count` 系 KPI、`outcome`、`tags` |
| `note` | `pj_slug` `date` `period` | `tags` |
| `insight` | `period`（または `slice`）`sources` `created` | `tags` |

### 3.2 `insight` の `slice`（横串の選択条件）

`master/insights/*.md` は **CSV のどの行を見ているか**を frontmatter に書きます。

```markdown
---
type: insight
slice:
  script_id: pkh_v3
  period: 2026-04
sources:
  - _analytics/master/cross_pj_kpi.csv
created: 2026-05-04
---
```

`build_master_kpi.py` は `slice` を見て、CSV から該当行だけを切り出して MD 末尾に **再現フィルタ**を追記できます（任意）。

## 4. `cross_pj_kpi.csv` のカラム

`master/cross_pj_kpi.csv` は縦に積む形式。各行は **PJ × 月 × ソース MD（あれば）**。

| カラム | 例 | 由来 |
|--------|-----|------|
| `pj_slug` | `PJname_20260415` | フォルダ名 |
| `year` | `2026` | フォルダ名 |
| `period` | `2026-04` | metrics.json の periods キー |
| `script_id` | `pkh_v3` または空 | scripts/*.md frontmatter |
| `call_count` | `412` | metrics.json または MD frontmatter |
| `connect` | `87` | 同上 |
| `appoint` | `12` | 同上 |
| `uketsuke_ng` | `95` | 同上 |
| `keyman_ng` | `47` | 同上 |
| `shiryou_soufu` | `18` | 同上 |
| `call_minutes` | `880` | metrics.json |
| `work_minutes` | `1980` | metrics.json |
| `source_md_path` | `_analytics/by-pj/2026/PJname_20260415/scripts/pkh_v3.md` または空 | 集計の逆引き |
| `source_metrics_json` | `_analytics/by-pj/2026/PJname_20260415/metrics.json` または空 | 同上 |
| `built_at` | ISO8601 | ビルド時刻 |

`kpi_by_month.csv` は `cross_pj_kpi.csv` を `period` で集計したもの（`build_master_kpi.py` が同時生成）。

## 5. 数値の正本ルール（重要）

- **同じ数値を `metrics.json` と MD frontmatter の両方に書かない**。原則は次の使い分け。
  - **PJ 全体の月次 KPI** … `metrics.json`（PJ ごと、機械集計の正本）
  - **個別の通話・スクリプト試行 ×成果** … MD frontmatter（粒度の細かい一次情報）
- `metrics.json` は **MD frontmatter の合算と一致するべき**だが、運用上は **`metrics.json` を上位の正本**として扱う（差分があれば人が確認）。
- ビルダ（`build_master_kpi.py`）は **両方を読み込み**、行ごとに `source_md_path` か `source_metrics_json` を立てて出力する（どちらが効いた行か追跡可能にする）。

## 6. 命名規約

- **`pj_slug`**: `PJname_yyyymmdd`（PJ 開始日 8 桁）。`-` は使わずアンダースコアのみ。
- **transcripts ファイル名**: `<yyyymmdd>_<short>.md`（例: `20260415_lead_call_001.md`）
- **scripts ファイル名**: `<script_id>.md`（同 PJ 内で `script_id` は一意）
- **notes ファイル名**: `<yyyymmdd>_<topic>.md`
- **insights ファイル名**: `<yyyy>Q<n>_<topic>.md`（年・四半期・トピックの順）

## 7. 冪等性（壊れたら全消し再生成）

- `_analytics/master/` と `_analytics/manifest/` は `scripts/build_master_kpi.py` の **唯一の書き込み先**。
- スクリプトは「既存ファイルを尊重しない・常に上書き」で実装する（**冪等**）。
- 一次情報（`by-pj/.../*.md` / `metrics.json`）は **手書き or Zoom 文字起こしの差分DL**でしか書き換えない。

## 8. 付録 A: `outcome` の固定語彙（暫定）

短く保つ。新語を増やす前に既存で言い換えできないか確認する。

- `アポ獲得` / `資料送付` / `キーマン不在` / `キーマンNG` / `受付NG` / `不通` / `保留` / `キーマン接続` / `その他`

## 9. 関連

- [re-design-2026-05.md](./re-design-2026-05.md) — 全体の RE 設計書
- [voice-pipeline.md](./voice-pipeline.md) — 文字起こし MD の生成元（Zoom）
- [db-drive-policy.md](./db-drive-policy.md) — DB / Drive / Local（`_analytics`）の三層方針
