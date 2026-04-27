/**
 * プロジェクト単位の「実行ツール」左ナビ定義。
 * 案件_SWW の IS メソッド抽出と、コールドコール〜MA・初回MTGディレクションを同一画面で育てる前提の初期骨子。
 */

export type ProjectToolId =
  | 'overview'
  | 'pipeline'
  | 'activity'
  | 'daily-report'
  | 'kpi-breakdown'
  | 'kpi-dashboard'
  | 'contact-appt'
  | 'cold-ma'
  | 'is-ops'
  | 'client-1st'
  | 'integrations'

export type ProjectToolSection = {
  id: ProjectToolId
  /** 左ナビ表示名 */
  label: string
  /** 1行説明 */
  summary: string
  /** メインパネル見出し */
  title: string
  /** 本文ブロック（後から DB 化しやすいフラット構造） */
  blocks: Array<{
    heading: string
    bullets: string[]
  }>
  /** 社外参照・前提（任意） */
  references?: string[]
}

const methodologyNote =
  '社内整理用: 案件_SWW「インサイドセールスメソッド_抽出」およびセレブリックス型（データ・ログに基づく営業プロセス言語化）の運用に沿って項目を増やす'

export const projectToolSections: ProjectToolSection[] = [
  {
    id: 'overview',
    label: '概要',
    summary: 'このツール群の目的と進め方',
    title: 'プロジェクト実行ツール',
    blocks: [
      {
        heading: '狙い',
        bullets: [
          '各プロジェクトの「管理・売上・アポイント率UP」を同じ画面で設計し、IS部隊とクライアントワーク（ディレクション）を接続する',
          '左ナビは機能単位で増やす。中身はチェックリストと運用メモから段階的にデータ化する',
          methodologyNote
        ]
      },
      {
        heading: '外部イメージ（セレブリックス）',
        bullets: [
          '大企業向けプロ営業支援としての「プロセスの言語化・標準化」とログ活用 — 自社ツールでは同じ思想でチェック項目を固定化する',
          '参照: https://www.cerebrix.jp/'
        ]
      }
    ],
    references: ['https://www.cerebrix.jp/']
  },
  {
    id: 'pipeline',
    label: '管理・売上',
    summary: '目標逆算・リスト供給・前倒し',
    title: '管理・売上（パイプライン）',
    blocks: [
      {
        heading: '目標からの逆算',
        bullets: [
          '月間目標を「営業日数」ではなく「営業日数−2日」などバッファ付きで日割りし前倒しで達成ラインを置く',
          '1社あたり平均架電回数（例: 3回）を置き、必要コール数から必要リスト数を算出する',
          '不測（欠勤・会議）を織り込み、リストの絶対数を月初で担保できているか'
        ]
      },
      {
        heading: '売上・案件管理に繋ぐメモ',
        bullets: [
          '商談化率・平均単価・サイクルをプロジェクトごとにメモ（数値は後からフォーム化）',
          'PeakHUB PJシート相当の「案件定義・体制・成果物」欄をここにマッピングする想定（Excel はリポジトリ外の場合は手元で列名を転記）'
        ]
      }
    ]
  },
  {
    id: 'activity',
    label: '活動量',
    summary: 'コール数・コアタイム・時間設計',
    title: '活動量（コールと時間）',
    blocks: [
      {
        heading: 'コール数不足の典型要因（対策の観点）',
        bullets: [
          'リスト精査や架電前リサーチがコアタイムに入り込んでいないか → 「架電する時間」と「リスト精査時間」を分離',
          '結果入力・トスアップ・報告メールがコアタイムを食っていないか',
          '時間あたりコール目標・デイリーコール目標が数値で固定されているか',
          '通話時間をリストに記録し、平均と計画に反映できているか'
        ]
      },
      {
        heading: '運用ルール',
        bullets: [
          '50分稼働 / 10分振り返り・確認 のリズムを切れるか',
          '30分ごとの目標コール数と実績を見られる仕組み（後続: ダッシュボード化）',
          '週初めに架電ブロックをカレンダーロックし、その枠に対して FB する'
        ]
      }
    ]
  },
  {
    id: 'daily-report',
    label: '日報',
    summary: '当日入力と直近ログ',
    title: '日報（入力）',
    blocks: [
      {
        heading: '入力するもの',
        bullets: [
          '架電件数 / 受付NG / キーマン接続 / キーマンNG / 資料送付 / アポ',
          '架電時間（分） / 稼働時間（分）',
          '上手くいった施策 / 次回施策 / NG理由メモ（後から構造化）'
        ]
      }
    ]
  },
  {
    id: 'kpi-breakdown',
    label: 'KPI内訳',
    summary: 'コンタクト率・プロセスMECE',
    title: 'KPI内訳（コンタクトまで）',
    blocks: [
      {
        heading: 'コンタクト率を分解する',
        bullets: [
          'ステータスを MECE にし、不在 / 受付NG / 現アナ / 別拠点 / なりっぱなし など内訳で要因特定',
          '曜日・時間帯別にプロセス集計し、架電しやすい帯を仮説→検証で更新',
          '番号不備・0発信・押し間違いなどオペミスを切り分ける'
        ]
      },
      {
        heading: 'リスト・エリア戦略',
        bullets: [
          '業界・課題が近い企業を固めて架電し、説明の再利用性を上げる',
          '難易度の高いエリアは情報武装（リサーチ上限時間のルール化）',
          '地方は件数稼ぎと難易度のトレードオフを設計'
        ]
      }
    ]
  },
  {
    id: 'kpi-dashboard',
    label: 'KPI',
    summary: '週次・月次の集計とボトルネック',
    title: 'KPIダッシュボード',
    blocks: [
      {
        heading: '改善の見る順',
        bullets: [
          'キーマン接続率 → 次アクション率 → NG理由上位',
          '週次（直近4週）と月次で推移を見る',
          'プレイヤー別とチーム合計で差分を見る'
        ]
      }
    ]
  },
  {
    id: 'contact-appt',
    label: 'アポ率UP',
    summary: 'コンタクトアポ・日時切り・切返し',
    title: 'アポイント率UP（コンタクトアポ）',
    blocks: [
      {
        heading: 'トーク構造',
        bullets: [
          '「インパクトアプローチ → 具体説明 → クロージング・日時切り」の順を守り、質問が来てからが本番と割り切る',
          '日時は「●日の▲時のご都合はいかがですか」とピンポイントで切る（思考を「空き」に誘導）',
          '回答の後は都度「一度お時間をいただけませんか？」でクロージング（同日時の繰り返しは避ける）'
        ]
      },
      {
        heading: '切返し・スクリプト',
        bullets: [
          '結論ファーストの回答スクリプトに落とす。録音レビューで最適解か検証',
          '想定NGごとに切返し集を持ち、切返すたびに直接話すメリットへ戻す',
          'ヒアリング項目は最大3つ程度に絞る',
          '機能ではなくメリット・権威・比較可能な事実で短くワンメッセージ化'
        ]
      },
      {
        heading: 'アポ獲得後',
        bullets: [
          '商談で「なぜアポに至ったか」をヒアリングし、勝ちパターンを横展開する'
        ]
      }
    ]
  },
  {
    id: 'cold-ma',
    label: 'CC〜MA',
    summary: 'コールドコールとマーケタッチの同時進行',
    title: 'コールドコール 〜 MA 施策',
    blocks: [
      {
        heading: 'コールドコール前後',
        bullets: [
          '事前 DM / 資料でフックを作り、「この電話は取り次ぐべき」用件に寄せる',
          '受付対応: 名前を聞く・戻り時間を聞く・次回の宛名を確認するアクションをスクリプトに明記',
          '用件が雑に聞かれたときの切り口（例: 急ぎでないので改める 等）は乱用しないルールもセットで',
          'SDR は架電後メールや QR 付き DM など、メール志向の相手への接点を設計'
        ]
      },
      {
        heading: 'MA と IS の同期',
        bullets: [
          'メール・フォーム・イベント・広告からのリードをリスト属性としてプロセス変数に紐づけ、同じダッシュボードで見る（後続実装）',
          'タッチポイントごとに反応率を記録し、架電スクリプトの前提を更新する'
        ]
      }
    ]
  },
  {
    id: 'is-ops',
    label: 'IS運用',
    summary: 'オペレーション・品質・チーム',
    title: 'IS 部隊オペレーション',
    blocks: [
      {
        heading: 'オペレーション効率',
        bullets: [
          'ヘッドセット＋架電しながら入力。プルダウン・ショートカット・単語登録でフリー記述を減らす',
          'リサーチ結果はリスト列に残し、同じ企業を何度も調べない',
          '報告メール本文テンプレを項目化し、ワンクリック起動できるようにする（後続: 自動化）'
        ]
      },
      {
        heading: '品質',
        bullets: [
          'ロープレでスクリプトを腹落ちさせる。ノイズ語（「えー」等）は録音で指摘し合う',
          '受付の名前を聞きメールに記載するなど、受付を味方にする行動をチェックリスト化'
        ]
      }
    ]
  },
  {
    id: 'client-1st',
    label: '初回MTG',
    summary: 'クライアントワーク / 1st チェックポイント',
    title: 'クライアントワーク（1st MTG チェックポイント）',
    blocks: [
      {
        heading: 'ディレクションで伝えること（初期チェック）',
        bullets: [
          '目的・成功定義・KPI（コンタクト率 / コンタクトアポ率 / 商談化）の合意',
          'コアタイム、リスト供給、リードソース（MA/リスト購入/既存）の責任分界',
          'スクリプト v0、切返し集、禁止表現・NGワードのすり合わせ',
          '報告粒度（日次・週次）とエスカレーションルール',
          '録音・ロープレ・レビュー会の頻度と参加者',
          '初月の前倒し計画（営業日バッファ・必要リスト数）の提示'
        ]
      },
      {
        heading: '1st MTG 後のアクション',
        bullets: [
          '左ナビ各セクションに「プロジェクト固有メモ」欄を今後追加し、合意事項を固定化する',
          'PeakHUB PJシートの項目と 1:1 で対応付けできるよう列マッピング表を作る'
        ]
      }
    ]
  },
  {
    id: 'integrations',
    label: '連携',
    summary: 'PJシート・外部データ',
    title: '外部連携（予定）',
    blocks: [
      {
        heading: 'PeakHUB / シート連携',
        bullets: [
          'リポジトリ内に `PeakHubPJｼｰﾄ Ref.xlsx` が無い場合: 手元ファイルのシート名・列名をここに貼り、取り込み仕様を決める',
          'CSV エクスポート → 取り込み、または API 連携のどちらで行くかをプロジェクトごとに記録する（実装は次フェーズ）'
        ]
      },
      {
        heading: 'CRM / MA',
        bullets: [
          '接続先（HubSpot / SF / Marketo 等）と同期フィールドを列挙し、IS リストのマスタを一本化する'
        ]
      }
    ]
  }
]

const defaultToolId: ProjectToolId = 'overview'

/** URL の `tool` クエリを正規化 */
export const normalizeProjectToolId = (raw: string | null | undefined): ProjectToolId => {
  const id = (raw ?? '').trim() as ProjectToolId
  return projectToolSections.some((s) => s.id === id) ? id : defaultToolId
}

/** 左ナビ用の軽量一覧 */
export const projectToolNavItems = projectToolSections.map((s) => ({
  id: s.id,
  label: s.label,
  summary: s.summary
}))

export const getProjectToolSection = (id: ProjectToolId): ProjectToolSection | undefined =>
  projectToolSections.find((s) => s.id === id)
