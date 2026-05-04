# reception-breakthrough

受付突破モジュール（実装側）。設計書は `docs/reception-breakthrough/` を参照。

> 本モジュールは「受付突破意思決定エンジン」。電話発信そのもの（Twilio 等）には依存しない。

## 設計書の位置

- インデックス: [`docs/reception-breakthrough/README.md`](../docs/reception-breakthrough/README.md)
- ステートマシン仕様: [`docs/reception-breakthrough/state-machine-spec.md`](../docs/reception-breakthrough/state-machine-spec.md)
- intent 改善仕様: [`docs/reception-breakthrough/intent-improvement-spec.md`](../docs/reception-breakthrough/intent-improvement-spec.md)
- 実装バックログ: [`docs/reception-breakthrough/implementation-backlog.md`](../docs/reception-breakthrough/implementation-backlog.md)

> 用語: **モジュール (module)** = 単独で動作する独立した機能のまとまり。本モジュールは他システムへ組み込めるよう、`crm_adapter` を境界として外部 CRM と切り離されている。

## ディレクトリ構成

```
reception-breakthrough/
├── app/          # エントリポイント・設定・スケジューラ
├── core/         # state machine / intent classifier / response builder / call controller
├── voice/        # 録音・文字起こし・音声合成・補助
├── infra/
│   ├── db/       # SQLite 接続・migration
│   ├── external/ # crm_adapter（外部 CRM の境界）/ telephony_port（将来差し替え）
│   └── logging/  # 構造化ログ
├── pipeline/     # 改善ループ（文字起こし job / ラベリング / 失敗分析 / metrics）
├── ui/           # FastAPI（後フェーズ）
├── data/         # ローカル成果物（recordings/transcripts/exports）
└── tests/
```

## 開発の進め方

実装は [`docs/reception-breakthrough/implementation-backlog.md`](../docs/reception-breakthrough/implementation-backlog.md) §5 の順番で進める。

1. **設計書を読む** — 該当する章を先に読む
2. **設計書を直す** — 仕様変更が必要なら設計書を先に修正してバックログを更新
3. **実装する** — DoD を満たすまで閉じない

> 用語: **DoD (Definition of Done)** = タスクの完了条件。これを満たさないと次へ進まない。

## 開発環境セットアップ

```bash
cd reception-breakthrough
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests/
```

## 不変条件（実装で必ず守る）

[`docs/reception-breakthrough/README.md` §3](../docs/reception-breakthrough/README.md#3-設計上の不変条件必読) を参照。要約:

1. 電話回線 API（Twilio 等）に依存しない
2. AI モードと HUMAN モードでロジック分岐しない
3. 既存 CRM DB へ直接書かない（必ず `crm_adapter` 経由）
4. 改善ループ用データは専用 SQLite に保存
5. テンプレ返答は「行動要求」で終える

## 現在のフェーズ

`T-001` 完了 — 雛形のみ。各ファイルは後続タスク（T-100 以降）で実装される。
