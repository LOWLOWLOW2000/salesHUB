## 目的

`sales_hub` は、社内向けのドキュメント閲覧・管理（KPI / slides / visuals など）を、**Google OAuth 認証**と**ロールベースアクセス制御（RBAC）**で安全に提供することを主目的とする。

このファイルは、Windows 側で運用していた前提を含めて、現行コード（WSL側）から読み取れる「設計思想」を引き継ぐためのメモ。

## 設計思想（Principles）

- **守る対象を先に決める**: “誰が何にアクセスできるか” を最上流の関心事として扱い、UI より先に認証・認可の境界を固める
- **防御を二段構えにする**: 入口（Basic）とアプリ内（OAuth + RBAC）を分離し、運用環境のリスクに応じて有効化できるようにする
- **運用で回る仕組みにする**: 許可メールのホワイトリストをDBで管理し、コード変更なしでオンボーディングできるようにする
- **役割はアプリの概念として永続化する**: ロールはセッションに埋め込まず、DBに正規化して扱う（監査・権限変更・将来拡張に強い）
- **スコープでデータを切る**: KPI は company/division/project のスコープを持つ前提でモデル化し、ユニーク制約で整合性を担保する

## 認証（Authentication）

### OAuth（Google）

- **プロバイダ**: Google
- **セッション戦略**: Database session
- **実装**: `src/lib/auth/nextAuth.ts`

Sign-in 時の方針は以下。

- **メールが空は拒否**
- **Managerメールは常に許可**（運用上のブレイクグラス枠）
- **それ以外は AllowedEmail に載っている場合のみ許可**

関連:

- `src/lib/auth/allowedEmail`（ホワイトリスト判定）
- `src/lib/auth/managerEmail`（管理者メール判定）

### 入口の Basic 認証（任意）

`src/middleware.ts` により、環境変数で設定されている場合のみ Basic 認証を要求する。

- **用途**: 検索エンジン・URL共有・一時公開など、OAuthだけでは不安な環境で“入口”を追加防御する
- **考え方**: OAuth/RBAC と独立した層に置き、必要なときだけONにできるようにする

## 認可（Authorization / RBAC）

### ロール

`prisma/schema.prisma` の `AppRole` を基準とする。

- `manager`
- `director`

ロールは “ユーザー単体” ではなく、以下の所属コンテキストに紐づく。

- **Companyロール**: `CompanyMember`
- **Projectロール**: `ProjectMember`

### 管理者ページ（Manager gate）

管理者向けのページは、`requireManager` により認可される。

- 実装: `src/lib/auth/requireManager.ts`
- **未ログイン**: `/api/auth/signin` にリダイレクト
- **ロール不足**: `/` にリダイレクト

この関数は「ページ側で使うガード」として、認証・認可の意図を集約するために存在する。

## データモデル（Prisma / SQLite）

### ストレージ方針

- **DB**: SQLite（`DATABASE_URL`）
- **目的**: まず運用と開発速度を優先し、KPI/ユーザー/セッション/RBAC を永続化する

### KPIの設計

`KpiDefinition` は以下を持つ。

- **スコープ**: `company | division | project`（`KpiScopeType`）
- **粒度**: `week | month`（`KpiGranularity`）
- **ユニーク性**: `scopeType + companyId + divisionId + projectId + code`

`KpiActual` は以下を持つ。

- **期間キー**: `periodType + periodStart`
- **重複防止**: `kpiDefinitionId + periodType + periodStart + sourceRef`

この構造により「同じスコープ・同じKPIコードは1定義」「同じ期間・同じソースの実績は1件」を担保する。

## 環境変数（運用前提）

最低限、OAuth を動かすために以下が必要。

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `DATABASE_URL`

Basic 認証は、設定されているときのみ動作する想定（具体名は `src/lib/auth/basic` を参照）。

## Windows からの引き継ぎメモ

- `desktop.ini` が残っているため、過去に **Windows + Google Drive** 経由でディレクトリ管理していた痕跡がある
- 今後も “運用で回す” を優先するなら、許可ユーザーやロール付与は **DB操作（管理画面/バッチ）**で完結させる方針が整合的

