'use client'

import { signIn } from 'next-auth/react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useState } from 'react'

type Props = {
  googleEnabled: boolean
  credentialsEnabled: boolean
}

/**
 * Custom sign-in: Google OAuth link and optional email/password.
 */
export const SignInForm = ({ googleEnabled, credentialsEnabled }: Props) => {
  const router = useRouter()
  const searchParams = useSearchParams()
  const callbackUrl = searchParams.get('callbackUrl') ?? '/auth/after'
  const error = searchParams.get('error')

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const submitCredentials = async () => {
    setBusy(true)
    setLocalError(null)
    const res = await signIn('credentials', {
      email: email.trim().toLowerCase(),
      password,
      callbackUrl,
      redirect: false
    })
    setBusy(false)
    if (res?.error) {
      setLocalError('メールまたはパスワードが正しくありません')
      return
    }
    if (res?.ok && res.url) {
      router.push(res.url)
      router.refresh()
    }
  }

  if (!googleEnabled && !credentialsEnabled) {
    return (
      <p className="text-sm text-zinc-700">
        認証プロバイダが設定されていません。管理者に <code className="rounded bg-zinc-100 px-1">GOOGLE_*</code> または{' '}
        <code className="rounded bg-zinc-100 px-1">ENABLE_CREDENTIALS_AUTH</code> の設定を確認してください。
      </p>
    )
  }

  return (
    <div className="space-y-8">
      {error ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900">
          サインインに失敗しました。もう一度お試しください。
        </p>
      ) : null}

      {googleEnabled ? (
        <div className="space-y-2">
          <h2 className="text-sm font-semibold text-zinc-900">Google</h2>
          <button
            type="button"
            onClick={() => void signIn('google', { callbackUrl })}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            Googleでログイン
          </button>
        </div>
      ) : null}

      {credentialsEnabled ? (
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-zinc-900">メールとパスワード</h2>
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-zinc-800">メール</span>
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full max-w-md rounded-lg border border-zinc-200 px-3 py-2"
            />
          </label>
          <label className="block space-y-1 text-sm">
            <span className="font-medium text-zinc-800">パスワード</span>
            <input
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full max-w-md rounded-lg border border-zinc-200 px-3 py-2"
            />
          </label>
          {localError ? <p className="text-sm text-red-600">{localError}</p> : null}
          <button
            type="button"
            disabled={busy || email.trim().length === 0 || password.length === 0}
            onClick={() => void submitCredentials()}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            ログイン
          </button>
        </div>
      ) : null}
    </div>
  )
}
