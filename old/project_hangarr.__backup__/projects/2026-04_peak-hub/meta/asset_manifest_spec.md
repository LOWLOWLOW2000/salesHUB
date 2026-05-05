# asset_manifest.csv 仕様

`data_project/` 側から `PJ_asset_Data/<pj-slug>/` 配下の資料（PDF・録音・スライド等）を参照するためのインデックスCSV。

集計時にAIではなくプログラムで `lead_id` / `call_log_id` から物理ファイルを引けるようにする。

---

## 配置

```
data_project/projects/<YYYY-MM_pj-slug>/derived/asset_manifest.csv
```

参照される実ファイルはすべて以下の配下に置く:

```
PJ_asset_Data/<YYYY-MM_pj-slug>/
```

---

## カラム定義（13列）

| 列 | 型 | 必須 | 説明 |
|---|---|---|---|
| `asset_id` | string | ○ | このマニフェスト内の一意ID。`AST-` + 6桁ゼロ埋め連番（例: `AST-000001`） |
| `asset_type` | enum | ○ | `zoom_recording` / `transcript` / `report` / `slide` / `pdf` / `image` / `other` |
| `lead_id` | string |  | 紐つく企業の `lead_id`（例: `PEAK-000123`）。資料が企業単位の時のみ |
| `call_log_id` | string |  | 紐つく `CallLog.id`。1架電に対する資料の時のみ |
| `recording_ref` | string |  | `CallRecording.sourceRecordingRef`（Zoom側ID）。`asset_type=zoom_recording` の時のみ |
| `project_slug` | string | ○ | プロジェクトスラッグ（例: `2026-04_peak-hub`）。`PJ_asset_Data/<slug>/` 配下を意味する |
| `relative_path` | string | ○ | `PJ_asset_Data/<project_slug>/` からの相対パス（例: `zoom_recordings/PEAK-000123_20260428.mp4`） |
| `bytes` | int |  | ファイルサイズ（参考値） |
| `recorded_at` | ISO8601 |  | 録音・収録日時（録音以外は省略可） |
| `created_at` | ISO8601 | ○ | このマニフェスト行を作成した日時 |
| `status` | enum | ○ | `draft` / `final` / `archived` / `missing` |
| `sha1` | string |  | ファイルのSHA1ハッシュ（重複検知用、任意） |
| `notes` | string |  | 自由記述 |

---

## ファイル命名規則（PJ_asset_Data 側）

`relative_path` が以下の規則を満たしていれば、命名から `lead_id` / `recorded_at` を逆引きできる。

### 録音

```
zoom_recordings/{lead_id}_{YYYYMMDD}_{HHMMSS}.mp4
zoom_recordings/{lead_id}_{YYYYMMDD}_{HHMMSS}.vtt    # transcript
```

例:
- `zoom_recordings/PEAK-000123_20260428_150000.mp4`
- `zoom_recordings/PEAK-000123_20260428_150000.vtt`

### レポート（クライアント提出物）

```
reports/{project_slug}_{report_type}_{YYYY-MM}.pdf
```

例:
- `reports/peak-hub_monthly_2026-04.pdf`
- `reports/peak-hub_weekly_2026-W17.pdf`

### スライド・社内資料

```
slides/{YYYY-MM-DD}_{topic}.pdf
internal/{YYYY-MM-DD}_{topic}.{ext}
```

---

## 運用ルール

1. **資料の追加時は `PJ_asset_Data/` に置く → `build_asset_manifest.py` で再生成**
2. `asset_manifest.csv` は **生成物**。手で編集しない
3. ファイルが見つからなくなった行は `status=missing` に自動更新（削除はしない）
4. 1ファイル = 1行。同一ファイルを複数の `lead_id` に紐付けたい場合は同じ `relative_path` で別 `asset_id` を発番

---

## プログラムからの利用例

```python
import pandas as pd
from pathlib import Path

PJ_ASSETS_ROOT = Path("PJ_asset_Data")
manifest = pd.read_csv("data_project/projects/2026-04_peak-hub/derived/asset_manifest.csv")

# lead_id で絞り込み
recs = manifest[
    (manifest["lead_id"] == "PEAK-000123")
    & (manifest["asset_type"] == "zoom_recording")
    & (manifest["status"] != "missing")
]
paths = [PJ_ASSETS_ROOT / r["project_slug"] / r["relative_path"] for _, r in recs.iterrows()]
```
