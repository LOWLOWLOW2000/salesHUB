import Link from 'next/link'

/**
 * OAuth 設定手順を案内するヘルプページ。
 */
const OAuthSetupPage = () => (
  <main className="mx-auto max-w-3xl space-y-6 px-4 py-10">
    <header className="space-y-2">
      <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">OAuth 設定ガイド</h1>
      <p className="text-sm leading-6 text-zinc-600">
        Google ログインで必要な環境変数が不足していると、認証が失敗します。以下の手順で
        `salesHUB/.env.local` を設定してください。
      </p>
    </header>

    <section className="space-y-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">必要な環境変数</h2>
      <ul className="list-disc space-y-1.5 pl-5 text-sm text-zinc-700">
        {[
          'NEXTAUTH_SECRET',
          'NEXTAUTH_URL',
          'GOOGLE_CLIENT_ID',
          'GOOGLE_CLIENT_SECRET'
        ].map((key) => (
          <li key={key}>
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs text-zinc-800">{key}</code>
          </li>
        ))}
      </ul>
      <p className="text-sm leading-6 text-zinc-600">
        値は `salesHUB/.env.example` を参考にコピーし、Google Cloud Console で発行した認証情報へ置き換えてください。
      </p>
    </section>

    <section className="space-y-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <h2 className="text-sm font-semibold text-zinc-900">メールとパスワード（Credentials）</h2>
      <p className="text-sm leading-6 text-zinc-600">
        テストや社内運用で ID/パスワードを使う場合は <code className="rounded bg-zinc-100 px-1">ENABLE_CREDENTIALS_AUTH=true</code>（または{' '}
        <code className="rounded bg-zinc-100 px-1">1</code> / <code className="rounded bg-zinc-100 px-1">yes</code>
        ）を追加し、初回ユーザは <code className="rounded bg-zinc-100 px-1">npm run auth:bootstrap-user</code> で作成します。Google
        と併用する場合も、NextAuth のプロバイダが空にならないよう注意してください。
      </p>
    </section>

    <section className="space-y-3 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-zinc-600">設定後、次のコマンドでビルドと起動確認を行います。</p>
      <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-3 text-xs text-zinc-100">
        <code>{`cd salesHUB
npm run build
npm run dev`}</code>
      </pre>
    </section>

    <div className="flex gap-3">
      <Link href="/auth/error" className="rounded-md border border-zinc-300 px-3 py-2 text-sm text-zinc-700 hover:bg-zinc-50">
        エラーページへ戻る
      </Link>
      <Link href="/" className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-800">
        トップへ戻る
      </Link>
    </div>
  </main>
)

export default OAuthSetupPage
