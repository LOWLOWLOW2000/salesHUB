# salse_consulting ワークスペース

- **salesHUB** — 架電・プロジェクト（Postgres）
- **nextcrm-app** — CRM / Consulting（DB が正。資料の実体は外部）
- **project_hangarr** — 人 + AI の **作業ハブ**（軽量 raw・作成物。Drive の入口名／旧名 `data_project`）— [docs/project-hangarr.md](docs/project-hangarr.md)
- **PJ_asset_Data** — **重い実体**（PDF / PPTX / 録音 / 動画 / 画像）の Drive ミラー入口（Git 対象外）
- **call_rec** — **架電 RAW**（録音・リスト・export）の Drive ミラー入口（Git 対象外）
- **`_analytics/`** — ローカル限定の **解析倉庫**（PJ 横串の KPI と AI 解析。Git 対象外、派生物） — [docs/_analytics-spec.md](docs/_analytics-spec.md)

設計の全体像（なぜこの構成か、1000PJ 想定の理由づけ）は **[docs/re-design-2026-05.md](docs/re-design-2026-05.md)** を参照してください。  
役割分担・二重保管を避けるルールは **[docs/storage-coexistence.md](docs/storage-coexistence.md)** に集約しています。

## Drive ストレージ（3 本構成）

| 入口（ローカル） | Drive 役割 | Folder ID |
|------------------|-----------|-----------|
| `project_hangarr` | A: 人 + AI の作業ハブ（軽量 raw・作成物） | `1-ojsPDPdIZz6gelUBc5IhjIPvy9gllQq` |
| `PJ_asset_Data` | B: 重い実体（PDF / 録音 / 動画） | `144hJUwro1nQ-vRTwQ8yXV1mZs2Wfbsc2` |
| `call_rec` | C: 架電 RAW（録音・リスト・export） | `1q0AXfEkSi3GQEQ1J7U330SanXokQxqTe` |

それぞれ Folder ID・サブフォルダ例・同期コマンドは **[docs/drive-data-hub.md](docs/drive-data-hub.md)** に集約しています。  
リンク切れのときは次のスクリプトで張り直します。

- **`bash scripts/setup_project_hangarr_symlink.sh "<A の WSL 絶対パス>"`** — `project_hangarr` を A へ
- **`./scripts/link_pj_asset_data.sh "<B の WSL 絶対パス>"`** — `PJ_asset_Data` を B へ
- 架電 RAW は `bash scripts/run_sync_call_raw.sh` で C → `call_rec/` に取り込み

## ローカル限定の解析倉庫 `_analytics/`

PJ 横串の KPI と AI 解析の倉庫です。**Drive には載せない**（派生物のため）。

- 仕様（`metrics.json` と MD frontmatter のスキーマ）: [docs/_analytics-spec.md](docs/_analytics-spec.md)
- 音声 → 文字起こしの取り込み（Zoom 自動文字起こし + 毎朝06:00 巡回）: [docs/voice-pipeline.md](docs/voice-pipeline.md)
- DB / Drive / Local（`_analytics`）の三層方針: [docs/db-drive-policy.md](docs/db-drive-policy.md)

セットアップと同期手順は **[scripts/README_drive_sync.md](scripts/README_drive_sync.md)** を参照してください。
