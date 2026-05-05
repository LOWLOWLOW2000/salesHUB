# 2026-04_peak-hub — 機械向け入口

## slug

- **フォルダ slug**: `2026-04_peak-hub`
- **PJ_asset_Data**: `PJ_asset_Data/<slug>/` を正とする（Drive 側フォルダ名が異なる場合は `README.md` の対応表を参照）

## 正本（storage-coexistence 要約）

| 種類 | 正本 |
|---|---|
| 軽量 raw（スプシ CSV export 等） | この PJ の `raw/` |
| 資料実体（PDF・録音・スライドの実ファイル） | `PJ_asset_Data/<slug>/` |
| 架電リスト・架電結果・CRM | NextCRM / salesHub（Postgres） |
| 全案件横断 CSV スナップショット | `data_project/master/`（`export_master_data.py`） |

## よく使うコマンド

マニフェスト（リポ共通スクリプト）:

```bash
cd data_project/scripts
python build_asset_manifest.py --slug 2026-04_peak-hub
```

投入用 CSV（この PJ の `tools/`）:

```bash
cd data_project/projects/2026-04_peak-hub/tools
.venv/bin/python src/generate_intake_csv.py --source baseconnect
# 出力デフォルト: ../derived/intake/
```

## AI / 検索で先に読む meta

- `meta/csv_spec.md`
- `meta/asset_manifest_spec.md`

人向けの背景・運用は `README.md`。
