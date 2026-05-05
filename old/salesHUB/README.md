# salesHUB CRM

AI-Augmented The Model + RevOps 方針の社内 CRM（**PostgreSQL** / Next.js 16 / Prisma 6 / NextAuth）。

## セットアップ

1. **PostgreSQL**  
   `docker compose up -d`（ポート **5433**）

2. **環境変数**  
   `.env.example` を `.env.local` にコピーして値を埋める。

   - `DATABASE_URL` … 例: `postgresql://saleshub:saleshub@localhost:5433/saleshub?schema=public`
   - `NEXTAUTH_SECRET` / `NEXTAUTH_URL`
   - `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`
   - `GM_EMAIL` … このメールはサインイン時に `CompanyMember(gm)` が付与される
   - `ENABLE_CREDENTIALS_AUTH` … `true` / `1` / `yes` でメール＋パスワードログインを有効化（**少なくとも Google か Credentials のどちらか**がプロバイダとして登録される必要がある。Google を外す運用ならこれを `true` にする）
   - その他ユーザは `AllowedEmail` に登録（Admin）またはブートストラップ時に自動 upsert

3. **Credentials 初回ユーザ（任意）**  
   `ENABLE_CREDENTIALS_AUTH=true` を入れたうえで、メール・パスワードを DB に載せる:

   ```bash
   CREDENTIALS_BOOTSTRAP_EMAIL='you@example.com' CREDENTIALS_BOOTSTRAP_PASSWORD='…' npm run auth:bootstrap-user
   ```

   既に Google だけで同じメールのユーザがある場合は、意図明示のため  
   `CREDENTIALS_BOOTSTRAP_ALLOW_EXISTING_GOOGLE_USER=true` を付けないと中止される。

4. **マイグレーション**

   ```bash
   npx prisma migrate deploy
   ```

5. **開発**

   ```bash
   npm install
   npm run dev
   ```

## 主な機能

| 領域 | 説明 |
|------|------|
| RBAC | `gm` / `manager` / `director` / `as` / `is` / `fs` / `cs`（ティア定義は `schema.prisma` の `AppRole`） |
| Master lists | CSV インポート、`SalesAccount`（`clientRowId`）へ upsert |
| 架電ルーム | `/sales-room/[projectId]?listId=` … iframe + 結果記帳 → `CallLog` |
| Zoom | `/api/zoom/dial`（S2S 設定時は実会議、未設定は mock）`/api/zoom/webhook` |
| KPI | 日報 + **CallLog** をダッシュボードに表示、改善示唆 |
| GM | `/admin/company-overview` で全案件集計 |
| 資料 | `/materials` … CSV 出力、SMTP 設定時は GM がメール送信 API |

## メモ

- **スプレッドシート同期**（`/api/lists/sync-sheet`）はユーザーの Google OAuth トークンが必要。Credentials のみのログインでは利用できない（CSV インポートは可）。
- Prisma は **6.19**（Node 20.18 環境との互換）。DB はプランどおり **PostgreSQL**。
- 本体はリポジトリ内の `salesHUB/` ディレクトリ（親リポジトリと別リポに切り出し可能）。
