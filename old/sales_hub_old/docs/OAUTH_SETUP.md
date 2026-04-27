# Google OAuth セットアップ（sales_hub）

ローカルおよび本番で Google ログインを動かすための手順と、はまりどころの整理です。

## 前提

- NextAuth（Auth.js 互換）+ Prisma Adapter + **Database session**
- 実装の中心: `src/lib/auth/nextAuth.ts`

## 1. Google Cloud Console

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを選択（または新規作成）。
2. **API とサービス** → **OAuth 同意画面** でアプリを設定（内部ユーザー限定でも可）。
3. **認証情報** → **認証情報を作成** → **OAuth 2.0 クライアント ID**。
4. アプリケーションの種類は **ウェブアプリケーション**。
5. **承認済みのリダイレクト URI** に、次を**その環境のオリジン付きで**追加する。

| 環境 | 追加する URI（例） |
|------|---------------------|
| ローカル | `http://localhost:3000/api/auth/callback/google` |
| 本番 | `https://あなたのドメイン/api/auth/callback/google` |

- ポートやホストが違う（例: `http://127.0.0.1:3000`）場合は、**実際にブラウザで開く URL と完全一致**する URI を追加する。未登録だと Google 側で `redirect_uri_mismatch` になりログインできない。

## 2. 環境変数（`.env.local`）

`sales_hub/.env.example` をコピーして `.env.local` を作り、次を埋める。

| 変数 | 説明 |
|------|------|
| `DATABASE_URL` | SQLite 例: `file:./dev.db`（実体は `prisma/` 基準で `sales_hub/prisma/dev.db`）。 |
| `NEXTAUTH_URL` | アプリの公開 URL。**ログイン時にブラウザが使うオリジンと一致**（例: `http://localhost:3000`）。末尾スラッシュなし推奨。 |
| `NEXTAUTH_SECRET` | ランダムな長い文字列（本番は `openssl rand -base64 32` など）。 |
| `GOOGLE_CLIENT_ID` | Console で発行したクライアント ID。 |
| `GOOGLE_CLIENT_SECRET` | クライアント シークレット。 |
| `MANAGER_EMAIL` | **初回ブレイクグラス**。この Google アカウントのメール（小文字比較）と一致するユーザーは、DB の `AllowedEmail` に無くてもサインイン可。入社後は `AllowedEmail` 運用に寄せる想定。 |
| `GOOGLE_OAUTH_SCOPES` | 任意。未設定時は `openid email profile`。 |
| `GOOGLE_REQUIRED_SCOPES` | 任意。カンマ区切りで追加必須スコープを指定すると、付与されていない場合 `/auth/after` で再接続を促す。 |

`.env.local` は Git に含めない（秘密情報のため）。

## 3. 誰がログインできるか

`signIn` コールバックのルール:

1. Google からメールが取れない → **拒否**。
2. メールが `MANAGER_EMAIL`（環境変数・大小無視）と一致 → **許可**。
3. それ以外 → DB の `AllowedEmail` に同一メールがある場合のみ **許可**。

そのため、**MANAGER_EMAIL も AllowedEmail も無いメールでは、Google 認証は通ってもアプリ側で拒否**され、`AccessDenied` 扱いになる。管理者にメールを登録してもらうか、一時的に `MANAGER_EMAIL` を自分に設定する。

## 4. ログイン直後の流れ

1. Google 認証成功後、NextAuth の `redirect` により **`/auth/after`** へ。
2. `GOOGLE_REQUIRED_SCOPES` が設定されている場合、トークンに必要スコープが無いと **再接続画面**（同じページ内）。「再接続する」で再同意。
3. オンボーディング未完了なら **`/onboarding`**。
4. 完了済みなら **`/`**。

## 5. トラブルシューティング

| 症状 | 確認すること |
|------|----------------|
| Google 画面で `redirect_uri_mismatch` | リダイレクト URI が Console の設定と完全一致しているか。`localhost` と `127.0.0.1` は別物。 |
| アプリに戻ったが「アクセス拒否」系 | メールが `MANAGER_EMAIL` または `AllowedEmail` にあるか。 |
| セッションが張れない / コールバック後にエラー | `NEXTAUTH_URL` が実際のオリジンと一致しているか。`NEXTAUTH_SECRET` が設定されているか。 |
| 追加スコープを求められるループ | `GOOGLE_REQUIRED_SCOPES` の値と、Google 側で実際に付与された scope（`/auth/after` の表示）を照合。 |

アプリ内の短い案内: **`/docs/oauth-setup`**。

## 関連ドキュメント

- [ARCHITECTURE.md](./ARCHITECTURE.md) — 認証・RBAC の全体像。
