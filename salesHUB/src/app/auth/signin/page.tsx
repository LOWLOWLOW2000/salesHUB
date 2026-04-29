import { Suspense } from 'react'
import Link from 'next/link'
import { SignInForm } from '@/app/auth/signin/SignInForm'
import { isCredentialsAuthEnabled, isGoogleOAuthConfigured } from '@/lib/auth/authProvidersEnv'

export default function SignInPage() {
  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-950">サインイン</h1>
        <p className="text-sm text-zinc-600">
          <Link href="/" className="text-zinc-700 underline hover:text-zinc-950">
            トップへ戻る
          </Link>
        </p>
      </div>
      <Suspense fallback={<p className="text-sm text-zinc-600">読み込み中…</p>}>
        <SignInForm
          googleEnabled={isGoogleOAuthConfigured()}
          credentialsEnabled={isCredentialsAuthEnabled()}
        />
      </Suspense>
    </div>
  )
}
