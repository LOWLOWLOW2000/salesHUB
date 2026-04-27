import type { Metadata } from 'next'
import Link from 'next/link'

export const metadata: Metadata = {
  title: 'Googleログインのセットアップ'
}

/**
 * OAuth セットアップ要約（リポジトリの docs/OAUTH_SETUP.md と対応）
 */
export default function OAuthSetupDocPage() {
  return (
    <div className="space-y-8 text-sm leading-6 text-zinc-700">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">Googleログインのセットアップ</h1>
        <p className="max-w-2xl">
          詳細な手順はリポジトリ内の <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">sales_hub/docs/OAUTH_SETUP.md</code>{' '}
          を参照してください。ここでは最低限のチェックリストだけ載せます。
        </p>
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-zinc-950">Google Cloud Console</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>OAuth 2.0 クライアント（ウェブ）を作成する。</li>
          <li>
            承認済みリダイレクト URI に、次を<strong>実際に使うオリジン付きで</strong>追加する:{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">/api/auth/callback/google</code> まで含む URL（例:{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">http://localhost:3000/api/auth/callback/google</code>）。
          </li>
          <li>
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">localhost</code> と{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">127.0.0.1</code> は別扱いのため、ブラウザの URL と一致させる。
          </li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-zinc-950">環境変数（.env.local）</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">NEXTAUTH_URL</code> はブラウザで開くベース URL と一致（末尾スラッシュなし推奨）。
          </li>
          <li>
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">NEXTAUTH_SECRET</code>、{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">GOOGLE_CLIENT_ID</code>、{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">GOOGLE_CLIENT_SECRET</code> を設定する。
          </li>
          <li>
            初回ログイン用: <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">MANAGER_EMAIL</code> に自分の Google
            メールを入れると、DB の許可リストが空でもサインインできる（ブレイクグラス）。
          </li>
          <li>
            任意: <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">GOOGLE_REQUIRED_SCOPES</code> を設定すると、不足時に{' '}
            <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">/auth/after</code> で再接続を促す。
          </li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold text-zinc-950">ログインできないとき</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>
            Google 側で拒否されていないか。アプリ側では、<code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">MANAGER_EMAIL</code>{' '}
            でも <code className="rounded bg-zinc-100 px-1.5 py-0.5 text-xs">AllowedEmail</code> にも載っていないメールはサインイン不可。
          </li>
          <li>リダイレクト URI の不一致は Google のエラーメッセージに出やすい。</li>
        </ul>
      </section>

      <div className="flex flex-wrap gap-2 pt-2">
        <Link
          href="/api/auth/signin"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          ログインへ
        </Link>
        <Link href="/" className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300">
          トップへ
        </Link>
      </div>
    </div>
  )
}
