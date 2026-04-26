import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { hasAllScopes, parseOAuthScope, requiredGoogleScopes } from '@/lib/auth/oauthScope'
import { getUserWorkspaceState } from '@/lib/onboarding/workspace'

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

  // #region agent log
  fetch('http://127.0.0.1:7856/ingest/3e0179af-86ed-44f9-a964-100da3275e33',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'44ec37'},body:JSON.stringify({sessionId:'44ec37',runId:'pre-fix',hypothesisId:'H-B',location:'src/app/auth/after/page.tsx:16',message:'auth/after session check',data:{hasSession:Boolean(session),hasUser:Boolean(session?.user),hasUserId:Boolean(userId)},timestamp:0})}).catch(()=>{})
  // #endregion

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
            追加の権限（スコープ）が必要なため、再度Google連携を行ってください。
          </p>
        </div>

        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-800">
          <div className="text-xs font-semibold text-zinc-600">必要</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {required.map((s) => (
              <span key={s} className="rounded-md bg-zinc-100 px-2 py-1 text-xs">
                {s}
              </span>
            ))}
          </div>

          <div className="mt-4 text-xs font-semibold text-zinc-600">付与済み</div>
          <div className="mt-1 flex flex-wrap gap-2">
            {granted.length === 0 ? (
              <span className="text-xs text-zinc-600">(取得できませんでした)</span>
            ) : (
              granted.map((s) => (
                <span key={s} className="rounded-md bg-zinc-100 px-2 py-1 text-xs">
                  {s}
                </span>
              ))
            )}
          </div>
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

  const state = await getUserWorkspaceState(userId)
  if (!state.onboardingCompleted) redirect('/onboarding')

  redirect('/')
}

