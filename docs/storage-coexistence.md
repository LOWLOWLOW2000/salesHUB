# Drive 3 本 + ローカル `_analytics/` の共存（二重保管を避ける）

作業リポジトリ（`salse_consulting`）が依存する **Drive 3 本**（A/B/C）と **ローカル限定 `_analytics/`** を整理し、**同じデータが複数箇所で正本を主張しないため**のルールです。

設計の全体像と理由づけは **[re-design-2026-05.md](./re-design-2026-05.md)** を参照してください。

## 1. 役割の早見表

| 入口（ローカル） | 種別 | Drive 役割 | Folder ID |
|------------------|------|------------|-----------|
| `project_hangarr` | Drive シンボリックリンク | **A: 作業ハブ**（軽量 raw・作成物） | `1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq` |
| `PJ_asset_Data` | Drive シンボリックリンク | **B: 重い実体**（PDF / 録音 / 動画 / PPTX） | `144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2` |
| `call_rec` | Drive シンボリックリンク | **C: 架電 RAW**（録音・リスト・export） | `1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe` |
| `_analytics/` | ローカル派生物 | **PJ 横串の KPI と AI 解析倉庫**（Drive へは載せない） | （ローカル） |

役割は重ならないように切り、**実体は1つ・派生物は再生成可**を徹底します。

## 2. 正本（Single source of truth）の割り当て

| データの種類 | 正本にする場所 | NextCRM の扱い |
|-------------|----------------|-----------------|
| PDF / PPTX / 画像 / 録音 / 動画 など **クライアント資料の実ファイル** | **`PJ_asset_Data`**（Drive B） | 実体は持たない。必要なら `CONSULTING_STORAGE_BASE_URL` + 相対キーで **URL の組み立てのみ**（`lib/saleshub/storage-refs.ts`） |
| **スプシの CSV エクスポート・スクリプト用の小さな raw** | **`project_hangarr/<year>/<pj_slug>/pj_sheet/`**（Drive A） | 対象外（DB や架電 UI とは別パイプライン） |
| **作成物**（HTML/CSS 下書き、AI 生成 MD など） | **`project_hangarr/<year>/<pj_slug>/generated/`**（Drive A） | 提出時に PDF 化など別プロセス |
| **架電リスト・架電結果・CRM 上の活動** | **NextCRM**（および salesHUB ブリッジの Postgres） | アプリ内が正 |
| **架電 RAW**（録音生データ・リスト・export 等） | **`call_rec/`**（Drive C） | 対象外（解析パイプライン側で消費） |
| **全案件横断の KPI / レポート（派生物）** | **`_analytics/master/`**（ローカル） | Drive へは載せない（再生成可） |

**禁止に近いこと**: 同じ PDF を「`PJ_asset_Data`（B）にフル同期」しつつ、`project_hangarr/.../gdrive_export/`（A）にも **同じファイルのコピー**として置き続ける運用（容量が二倍）。**重い実体は B に集約**し、A 側にコピーを作らない。

DB（正本）・Drive（提出物）・ローカル（同期/キャッシュ・派生）の三層方針は [db-drive-policy.md](./db-drive-policy.md) を参照。

## 3. シンボリックリンクで「そのまま」使う

- リポジトリ内の `project_hangarr` / `PJ_asset_Data` / `call_rec` は多くの環境で **シンボリックリンク**（Windows のマイドライブ配下の実フォルダへ）です。Git には含まれません（`.gitignore`）。
- **PJ フォルダ名**は、可能なら NextCRM の `consulting_Engagements.slug` と揃え、`PJname_yyyymmdd` 形式 + 年シャード（`2026/`）に統一します（命名規約は [_analytics-spec.md](./_analytics-spec.md) と [re-design-2026-05.md](./re-design-2026-05.md)）。

## 4. リンク切れ・初期セットアップ時の手順

各リンクの張替え方は次の通り（詳細は各スクリプトのヘッダ）。

- `project_hangarr` を A へ: `bash scripts/setup_project_hangarr_symlink.sh "<A の WSL 絶対パス>"`
- `PJ_asset_Data` を B へ: `./scripts/link_pj_asset_data.sh "<B の WSL 絶対パス>"`
- `call_rec` は同期で取り込み: `bash scripts/run_sync_call_raw.sh`

WSL から見える絶対パスの探し方の例（環境差あり）:

```bash
find /mnt/c/Users -maxdepth 6 -type d -name 'project_hangarr' 2>/dev/null
find /mnt/i -maxdepth 4 -type d -name 'project_hangarr' 2>/dev/null
```

## 5. NextCRM 側の設定（任意）

- `CONSULTING_STORAGE_BASE_URL` … ブラウザから開ける **HTTP(S) のベース URL**（末尾スラッシュなし）。ローカルディスクパスそのものは指定できません。
- 未設定のままでも、**ファイル実体は `PJ_asset_Data` / Drive が正**で問題ありません（Sales HUB 画面の説明どおり、ディープリンク生成だけスキップされます）。
- ブラウザからも同じ実ファイルを参照したい場合のみ、**`PJ_asset_Data` と同じディスク上のパスをルートにした静的配信**（社内 nginx、開発時のみの `serve` 等）を立て、その URL を `CONSULTING_STORAGE_BASE_URL` に合わせます。**ファイルは一箇所**に置き、URL はその窓口だけ増やすイメージです。

## 6. Drive 同期スクリプトとの関係

- `scripts/sync_drive_full.py` は **指定 Folder ID → 指定ローカルディレクトリへ片方向ミラー**します。役割を A/B/C で混ぜないでください。
- ラッパースクリプト:
  - `scripts/run_sync_pj_asset_data.sh` … B → `PJ_asset_Data/`
  - `scripts/run_sync_call_raw.sh` … C → `call_rec/`
  - （次フェーズ）`scripts/run_sync_project_hangarr.sh` … A → `project_hangarr/`
- スプシ等は **CSV で export した分だけ** A の `pj_sheet/` に置けば、B との二重化は起きません。

## 7. 参照

- [re-design-2026-05.md](./re-design-2026-05.md) — RE 設計書（全体像と理由づけ）
- [drive-data-hub.md](./drive-data-hub.md) — A / B / C の Folder ID と同期コマンド
- [project-hangarr.md](./project-hangarr.md) — `project_hangarr` の標準ツリー・Drive 同調
- [_analytics-spec.md](./_analytics-spec.md) — `_analytics/` のスキーマ
- [voice-pipeline.md](./voice-pipeline.md) — Zoom 自動文字起こし + 毎朝06:00 差分巡回
- [db-drive-policy.md](./db-drive-policy.md) — DB / Drive / Local（`_analytics`）三層方針
- `scripts/link_pj_asset_data.sh` — `PJ_asset_Data` を Drive B にリンク
- `scripts/setup_project_hangarr_symlink.sh` — `project_hangarr` を Drive A にリンク（退避→張替え推奨フロー）
- `scripts/run_sync_pj_asset_data.sh` — Drive B → `PJ_asset_Data`
- `scripts/run_sync_call_raw.sh` — Drive C → `call_rec/`
- `scripts/README_drive_sync.md` — Drive 同期手順
- `nextcrm-app/.env.example` — `CONSULTING_STORAGE_BASE_URL` / `SALES_HUB_DATABASE_URL`
