# reception-breakthrough

受付突破 AI モジュール。設計書は `docs/reception-breakthrough/` を参照。

> 本モジュールは「受付突破意思決定エンジン」。電話発信そのもの（Twilio 等）には依存しない。

---

## 設計書の位置

| ドキュメント | 概要 |
|---|---|
| [`docs/reception-breakthrough/README.md`](../docs/reception-breakthrough/README.md) | アーキテクチャ / 不変条件 |
| [`docs/reception-breakthrough/state-machine-spec.md`](../docs/reception-breakthrough/state-machine-spec.md) | S0〜S11 ステートマシン仕様 |
| [`docs/reception-breakthrough/intent-improvement-spec.md`](../docs/reception-breakthrough/intent-improvement-spec.md) | L1/L2 インテント分類 / C2 判定仕様 |
| [`docs/reception-breakthrough/implementation-backlog.md`](../docs/reception-breakthrough/implementation-backlog.md) | タスク T-000〜T-602 / DoD |

---

## ディレクトリ構成

```
reception-breakthrough/
├── app/
│   ├── config.py       # T-600: data/config.yaml を読む型付き設定
│   ├── main.py         # 将来のエントリポイント
│   └── scheduler.py    # 将来のジョブスケジューラ
├── core/
│   ├── state_machine.py    # T-200: S0〜S11 遷移ロジック
│   ├── intent_classifier.py# T-201: YAMLキーワードルールベース分類器
│   ├── response_builder.py # T-202: 語尾ローテーション付きテンプレート展開
│   └── call_controller.py  # T-203: オーケストレーター（SM + 分類器 + Builder）
├── voice/
│   ├── audio_utils.py  # T-302: 無音検出 / WAV 正規化
│   ├── recorder.py     # T-300: WAV 取り込み / call_recordings DB 登録
│   ├── transcriber.py  # T-301: whisper.cpp ラッパー / 話者分離
│   └── tts.py          # 将来: TTS（現在スタブ）
├── pipeline/
│   ├── transcription_job.py # T-400: 未処理録音の文字起こしバッチ（冪等）
│   ├── intent_labeling.py   # T-401: 未ラベル transcript へのインテント自動付与（冪等）
│   ├── failure_analysis.py  # T-402: 失敗セッション抽出 / failure_cases / CSV
│   └── metrics.py           # T-403: 日次スナップショット / INSERT OR REPLACE / CSV
├── ui/
│   └── api_server.py   # T-500: FastAPI REST API（架電画面バックエンド）
├── infra/
│   ├── db/
│   │   ├── local_db.py     # T-101: SQLite context manager / migration 自動適用
│   │   ├── migrations.sql  # T-100: スキーマ定義（全テーブル）
│   │   └── models.py       # 将来: ORM スタブ
│   ├── external/
│   │   ├── crm_adapter.py  # T-110: CRM 境界インターフェース + InMemoryCRMAdapter
│   │   └── telephony_port.py # 将来: 電話回線ポート（差し替え可）
│   └── logging/
│       └── logger.py       # T-102: JSON Lines 構造化ログ / session_id MDC
├── data/
│   ├── config.yaml         # T-600: 全設定値（マジックナンバーをここに集約）
│   ├── intent_keywords.yaml    # T-201: インテント別キーワード辞書
│   ├── response_templates.yaml # T-202: 返答テンプレート辞書
│   ├── exports/            # failure_cases_*.csv / metrics_*.csv 出力先
│   ├── recordings/         # WAV ファイル置き場
│   └── transcripts/        # 将来のテキスト出力置き場
└── tests/                  # pytest ユニット / 統合テスト群
```

---

## クイックスタート

```bash
# 1. リポジトリ直下の salse_consulting/ が作業ディレクトリの場合
cd reception-breakthrough

# 2. 仮想環境（venv）を作成・有効化
#    venv = 「Python のライブラリを他のプロジェクトと分けて管理する箱」
python3 -m venv .venv
source .venv/bin/activate        # Windows は .venv\Scripts\activate

# 3. 依存ライブラリをインストール
pip install -r requirements.txt

# 4. テスト全件実行
python -m pytest tests/ -v

# 5. API サーバー起動（開発モード）
uvicorn ui.api_server:app --reload --port 8000
# http://127.0.0.1:8000/docs — Swagger UI（ツールバーで英語 / 日本語スキーマ切替）
```

---

## API エンドポイント一覧（T-500）

| Method | Path | 説明 |
|--------|------|------|
| GET | `/health` | 死活確認 |
| GET | `/leads/next` | 次架電リードを 1 件取得 |
| POST | `/sessions` | 架電セッション開始（`EV_DIALED` 自動送信） |
| GET | `/sessions` | セッション一覧（`?limit=&offset=&outcome_id=`） |
| GET | `/sessions/{id}` | セッション詳細 |
| GET | `/sessions/{id}/transitions` | 状態遷移一覧 |
| GET | `/sessions/{id}/outcome` | アウトカム（未終了は 404） |
| POST | `/sessions/{id}/step` | インテント/イベント ID でステップ進める |
| POST | `/sessions/{id}/step_text` | 発話テキストを分類してステップ進める |
| GET | `/metrics/latest` | 日次メトリクス（`?target_date=YYYY-MM-DD`） |

---

## 改善ループジョブの使い方（T-400〜T-403）

```python
from pipeline.transcription_job import run_transcription_job
from pipeline.intent_labeling    import run_intent_labeling
from pipeline.failure_analysis   import run_failure_analysis
from pipeline.metrics            import run_metrics

# 全ジョブ冪等 — 毎日 cron で回してもデータが壊れない
run_transcription_job(db_path="data/calls.db")
run_intent_labeling(db_path="data/calls.db")
run_failure_analysis(db_path="data/calls.db", export_dir="data/exports")
run_metrics(db_path="data/calls.db", export_dir="data/exports")
```

---

## 設定のカスタマイズ（T-600）

`data/config.yaml` の値を変えるだけで動作が変わります。コードを触る必要はありません。

```yaml
silence:
  rms_threshold: 300       # 無音判定の閾値（小さくすると感度上がる）
  silence_limit_ms: 8000   # 累計無音がこれを超えると F2_silence

state_machine:
  unclear_limit: 3         # 聞き取り不可がこの回数連続で強制終了

classifier:
  min_confidence: 0.3      # これ未満は「不明（F1_unclear）」として扱う
```

---

## 不変条件（実装で必ず守る）

1. 電話回線 API（Twilio 等）に依存しない
2. AI モードと HUMAN モードでロジック分岐しない
3. 既存 CRM DB へ直接書かない（必ず `crm_adapter` 経由）
4. 改善ループ用データは専用 SQLite に保存（`data/calls.db`）
5. テンプレート返答は「行動要求」で終える（バリデーション済み）

---

## フェーズ完了状態

| フェーズ | タスク | 状態 |
|---------|--------|------|
| Phase 0 | T-000: ID 表記ゆれ修正 | ✅ 完了 |
| Phase 1 | T-001: スケルトン | ✅ 完了 |
| Phase 1 | T-100: DB スキーマ | ✅ 完了 |
| Phase 1 | T-101: SQLite 接続層 | ✅ 完了 |
| Phase 1 | T-102: 構造化ログ | ✅ 完了 |
| Phase 1 | T-110: CRM アダプター | ✅ 完了 |
| Phase 2 | T-200: ステートマシン | ✅ 完了 |
| Phase 2 | T-201: インテント分類器 | ✅ 完了 |
| Phase 2 | T-202: レスポンスビルダー | ✅ 完了 |
| Phase 2 | T-203: CallController | ✅ 完了 |
| Phase 3 | T-300: Recorder | ✅ 完了 |
| Phase 3 | T-301: Transcriber | ✅ 完了 |
| Phase 3 | T-302: AudioUtils | ✅ 完了 |
| Phase 4 | T-400: TranscriptionJob | ✅ 完了 |
| Phase 4 | T-401: IntentLabeling | ✅ 完了 |
| Phase 4 | T-402: FailureAnalysis | ✅ 完了 |
| Phase 4 | T-403: Metrics | ✅ 完了 |
| Phase 5 | T-500: API Server (FastAPI) | ✅ 完了 |
| Phase 6 | T-600: 設定外出し | ✅ 完了 |
| Phase 6 | T-601: 統合テスト | ✅ 完了 |
| Phase 6 | T-602: README | ✅ 完了 |
