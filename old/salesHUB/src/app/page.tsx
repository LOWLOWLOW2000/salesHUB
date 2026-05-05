import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { AppShell } from '@/app/_components/AppShell'
import { getAccessibleProjects } from '@/lib/projects/accessibleProjects'
import { getSidebarProfile } from '@/lib/auth/sidebarProfile'

export default async function Home() {
  const session = await getSession()
  const userId = session?.user?.id

  if (!userId) {
    return (
      <div className="space-y-6">
        <div className="space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">salesHUB</h1>
          <p className="max-w-2xl text-sm leading-6 text-zinc-700">
            AI-Augmented The Model と RevOps データ基盤で、IS / FS / CS / AS / Director を一つに揃えます。
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link
            href="/auth/signin"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            ログイン
          </Link>
          <Link
            href="/admin"
            className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
          >
            Admin
          </Link>
        </div>
      </div>
    )
  }

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      name: true,
      email: true,
      onboardingCompletedAt: true
    }
  })

  if (!user?.onboardingCompletedAt) redirect('/onboarding')

  const [projects, profile] = await Promise.all([getAccessibleProjects(userId), getSidebarProfile(userId)])

  return (
    <AppShell
      title="メイン"
      subtitle={[user.name ?? user.email ?? ''].filter((v) => v.length > 0).join(' / ')}
      projects={projects}
      profile={profile}
    >
      <div className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            { title: 'Master lists', description: 'CSV インポートと企業マスタ（SalesAccount）', href: '/master-lists' },
            { title: '架電ルーム', description: 'プロジェクト横のリスト架電（Project からリンク）', href: '#' },
            { title: 'KPI / 日報', description: '各 Project の実行ツールから', href: '#' },
            { title: '資料送付', description: 'カタログと CSV / メール送付ログ', href: '/materials' }
          ].map((c) => (
            <Link
              key={c.title}
              href={c.href === '#' ? '/' : c.href}
              className="rounded-2xl border border-zinc-200 bg-zinc-50 p-4 transition hover:border-zinc-300"
            >
              <div className="text-sm font-semibold">{c.title}</div>
              <div className="mt-1 text-sm leading-6 text-zinc-600">{c.description}</div>
            </Link>
          ))}
        </div>
      </div>
    </AppShell>
  )
}
