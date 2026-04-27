import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { hasAllScopes, parseOAuthScope, requiredGoogleScopes } from '@/lib/auth/oauthScope'

const getGoogleAccountScope = async (userId: string) => {
  const account = await prisma.account.findFirst({
    where: { userId, provider: 'google' },
    select: { scope: true }
  })

  return parseOAuthScope(account?.scope)
}

export default async function AuthAfterPage() {
  const session = await getSession()
  const userId = session?.user?.id

  if (!userId) redirect('/api/auth/signin')

  const required = requiredGoogleScopes()
  const granted = await getGoogleAccountScope(userId)
  const ok = hasAllScopes(granted, required)

  if (required.length > 0 && !ok) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">権限の確認が必要です</h1>
          <p className="max-w-2xl text-sm leading-6 text-zinc-700">
            追加の権限（スコープ）が必要なため、再度 Google 連携を行ってください。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            href="/api/auth/signin"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            再接続する
          </Link>
          <Link
            href="/api/auth/signout"
            className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
          >
            サインアウト
          </Link>
        </div>
      </div>
    )
  }

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { onboardingCompletedAt: true }
  })

  if (!user?.onboardingCompletedAt) redirect('/onboarding')

  redirect('/')
}
