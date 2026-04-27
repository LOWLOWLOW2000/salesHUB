import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { AppShell } from '@/app/_components/AppShell'
import { getAccessibleProjects } from '@/lib/projects/accessibleProjects'

export default async function Home() {
  const session = await getSession()
  const userId = session?.user?.id

  if (!userId) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">Sales Consulting Hub</h1>
          <p className="max-w-2xl text-sm leading-6 text-zinc-700">
            ログイン後に、クライアントワーク（案件/戦略戦術/1on1/評価/塾）と、自動部隊（IS01管理）を切り分けて運用します。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            href="/api/auth/signin"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            Googleでログイン
          </Link>
          <Link
            href="/admin"
            className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
          >
            Admin
          </Link>
        </div>

        <p className="text-sm text-zinc-600">
          <Link href="/docs/oauth-setup" className="font-medium text-zinc-900 underline-offset-2 hover:underline">
            ログインできない場合（Google OAuth のセットアップ）
          </Link>
        </p>
      </div>
    )
  }

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      name: true,
      email: true,
      onboardingCompletedAt: true,
      primaryWorkspace: { select: { type: true, name: true } }
    }
  })

  if (!user?.onboardingCompletedAt) redirect('/onboarding')

  const projects = await getAccessibleProjects(userId)

  return (
    <AppShell
      title="メイン"
      subtitle={[
        user.primaryWorkspace ? `${user.primaryWorkspace.name} (${user.primaryWorkspace.type})` : 'workspace未設定',
        user.name ?? user.email ?? ''
      ]
        .filter((v) => v.length > 0)
        .join(' / ')}
      projects={projects}
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { title: '案件管理', description: 'クライアントワークの案件を整理' },
            { title: '戦略戦術', description: '位相/戦術の検討と記録' },
            { title: '1on1', description: '面談ログとアクション' },
            { title: '評価', description: 'チーム評価・個人評価' },
            { title: '戦略苦戦塾', description: '学習/振り返りの運用' }
          ].map((c) => (
            <div key={c.title} className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4">
              <div className="text-sm font-semibold">{c.title}</div>
              <div className="mt-1 text-sm leading-6 text-zinc-600">{c.description}</div>
            </div>
          ))}
        </div>

        <div className="text-xs text-zinc-600">
          ※ ここから先の各機能ページは順次作っていきます
        </div>
      </div>
    </AppShell>
  )
}
