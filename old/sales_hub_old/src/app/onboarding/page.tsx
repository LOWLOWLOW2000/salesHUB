import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { getUserWorkspaceState } from '@/lib/onboarding/workspace'
import { OnboardingWizard } from './wizard'

export default async function OnboardingPage() {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const state = await getUserWorkspaceState(userId)
  if (state.onboardingCompleted) redirect('/app')

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">初期設定</h1>
        <p className="max-w-2xl text-sm leading-6 text-zinc-700">
          「クライアントワーク」と「自動部隊（IS01管理）」を分けて運用します。まず所属を選択してください。
        </p>
      </div>

      <OnboardingWizard />
    </div>
  )
}

