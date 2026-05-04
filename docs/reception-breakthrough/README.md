# Reception Breakthrough Module — 設計書インデックス

受付突破（コールドコール時の「受付」を抜けてキーマンへ取り次がせる）プロセスを、AI 自動架電と人力架電の両方で **同じステートマシン** に乗せて回すためのモジュール設計。

このディレクトリは **設計書のみ**（実装コードはここには置かない）。実装は Cursor 側でこの仕様を参照しながら `reception-breakthrough/`（リポジトリ root 直下）に作る前提。

> 用語: **ステートマシン (state machine)** = 「いまの状態」と「入ってきた合図」だけで次の状態を決める仕組み。会話の流れを `S2 → S3 → S6 → S7 → S8` のように離散的な箱で扱う。

---

## 1. 設計書 3 点セット

| ファイル | 役割 |
| --- | --- |
| [state-machine-spec.md](./state-machine-spec.md) | ステート一覧、遷移表、例外遷移、終了条件、ログ要件 |
| [intent-improvement-spec.md](./intent-improvement-spec.md) | 受付発話の intent 分類体系、C2 曖昧拒否の判定、改善ループ |
| [implementation-backlog.md](./implementation-backlog.md) | データ境界ルール、`crm_adapter` 契約、依存順タスクと DoD |

3 点セットは **同じ ID 体系** を共有する（下記 2 章）。新しい state や intent を増やすときは、まずここの ID を増やしてから各仕様書に反映する。

---

## 2. 共通 ID 体系（cross-reference keys）

各仕様書はここで定義された ID を **そのまま** 引用する。表記ゆれ禁止。

### 2.1 state_id（ステートマシンの状態）

| state_id | 名前 | 種別 |
| --- | --- | --- |
| `S0` | not_called | 初期 |
| `S1` | dialing | 進行 |
| `S2` | reception_contact | 進行 |
| `S3` | purpose_inquiry | 進行 |
| `S4` | rejected | 失敗系 |
| `S5` | rebuttal | 進行 |
| `S6` | transfer_request | 進行 |
| `S7` | on_hold | 進行 |
| `S8` | keyperson_connected | 成功 |
| `S9` | absent | 保留 |
| `S10` | callback_scheduled | 保留 |
| `S11` | terminated | 終了 |

### 2.2 intent_id（受付発話の意味ラベル）

L1（大分類） / L2（詳細）の二段。詳細は [intent-improvement-spec.md](./intent-improvement-spec.md)。

| L1 | L2 (intent_id) | 概要 |
| --- | --- | --- |
| A | `A1_listening` | 聞く姿勢あり |
| B | `B1_simple_purpose` / `B2_detailed_purpose` | 用件確認 |
| C | `C1_hard_reject` / `C2_soft_reject` / `C3_policy_block` | 拒否 |
| D | `D1_hold` / `D2_internal_check` / `D3_name_request` | 取次アクション |
| E | `E1_absent` / `E2_busy` / `E3_schedule` | 不在・時間 |
| F | `F1_unclear` / `F2_silence` / `F3_disconnect` | ノイズ |

### 2.3 outcome_id（通話セッションの最終結果）

| outcome_id | 意味 |
| --- | --- |
| `OUT_CONNECTED` | キーマン接続まで到達（`S8` で終了） |
| `OUT_REJECTED` | 受付段階で拒否確定（`S4` 連続 or `S5` 失敗から `S11`） |
| `OUT_ABSENT` | 不在のため再架電予約（`S10` で `S11`） |
| `OUT_NOISE` | 回線断・聞き取り不能などの異常終了（`F3` 等から `S11`） |

### 2.4 mode（架電主体）

`AI` / `HUMAN` の 2 値。同じ state machine を共有し、遷移トリガーだけ違う（AI は intent 自動分類、HUMAN はオペレーター操作）。

---

## 3. 設計上の不変条件（必読）

このモジュールは下記を **崩さない**。崩れたら設計から作り直す。

1. **電話回線 API（Twilio 等）に依存しない** — 通話入力は録音ファイル / 将来のリアルタイム入力を共通フォーマットで受ける
2. **AI モードと HUMAN モードでロジック分岐しない** — 遷移ルールは 1 本。学習データを統合するため
3. **既存 CRM DB へ直接書かない** — 必ず `crm_adapter` 経由（[implementation-backlog.md](./implementation-backlog.md) §3）
4. **改善ループ用データは専用 SQLite に保存** — 既存 CRM を肥大化させない
5. **テンプレ返答は「行動要求」で終える** — 説明で終わらせない（`response_template` 設計原則）

---

## 4. このモジュールがやらないこと

- 電話発信そのもの（呼び出し・通話制御）
- キーマン接続後の本商談（クロージング・ヒアリングは別モジュール）
- リードの新規開拓（既存 CRM のリードを参照するだけ）
- 営業電話の合法性チェック（法務観点は別管理）

---

## 5. 改訂履歴管理

各仕様書の冒頭にバージョン表を置く。state_id / intent_id を増減した場合は本 README の表を **先に** 更新する。
