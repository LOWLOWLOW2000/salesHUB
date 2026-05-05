import Link from 'next/link'

type Props = {
  searchParams: Promise<{ error?: string }>
}

const describeError = (code: string | undefined) => {
  switch (code) {
    case 'AccessDenied':
      return {
        title: 'サインインが拒否されました',
        body:
          'メールが許可リスト（AllowedEmail）に含まれるか、環境変数 GM_EMAIL と一致する必要があります。ID/パスワード（Credentials）で入る場合も同じ条件です。GM に登録を依頼するか、ローカルなら .env.local の GM_EMAIL / AllowedEmail を確認してください。'
      }
    case 'Configuration':
      return {
        title: '認証の設定に問題があります',
        body:
          'NEXTAUTH_SECRET / NEXTAUTH_URL は必須です。Google でログインする場合は GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET も必要です。メールとパスワードのみにする場合は ENABLE_CREDENTIALS_AUTH を有効にし、少なくとも Google か Credentials のどちらか一方のプロバイダが登録されるよう環境変数を揃えてください。'
      }
    case 'Verification':
      return {
        title: '検証トークンが無効です',
        body: 'リンクの有効期限が切れている可能性があります。もう一度サインインを試してください。'
      }
    default:
      return {
        title: 'サインインに失敗しました',
        body:
          'しばらくしてから再度お試しください。問題が続く場合は OAuth の設定（Google のリダイレクト URI）や メール/パスワード を確認してください。'
      }
  }
}

/**
 * NextAuth のエラーリダイレクト先（pages.error）
 */
export default async function AuthErrorPage({ searchParams }: Props) {
  const { error } = await searchParams
  const { title, body } = describeError(error)

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">{title}</h1>
        <p className="max-w-2xl text-sm leading-6 text-zinc-700">{body}</p>
        {error ? (
          <p className="text-xs text-zinc-500">
            エラーコード: <code className="rounded bg-zinc-100 px-1 py-0.5">{error}</code>
          </p>
        ) : null}
      </div>

      <ul className="max-w-2xl list-disc space-y-1 pl-5 text-sm text-zinc-700">
        <li>Google でログインする場合: Cloud Console の「承認済みのリダイレクト URI」に /api/auth/callback/google が登録されているか。</li>
        <li>NEXTAUTH_URL がブラウザのアドレスバーのオリジンと一致しているか。</li>
      </ul>

      <div className="flex flex-wrap gap-2">
        <Link
          href="/docs/oauth-setup"
          className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
        >
          セットアップ手順（要約）
        </Link>
        <Link
          href="/auth/signin"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          再度サインイン
        </Link>
        <Link href="/" className="rounded-lg px-4 py-2 text-sm font-medium text-zinc-600 hover:text-zinc-950">
          トップへ
        </Link>
      </div>
    </div>
  )
}
