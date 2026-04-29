import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import { AppShell } from '@/app/_components/AppShell'
import { getAccessibleProjects } from '@/lib/projects/accessibleProjects'
import { addMaterialAsset } from '@/app/materials/actions'
import { MaterialExportPanel } from '@/app/materials/MaterialExportPanel'

export default async function MaterialsPage() {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { onboardingCompletedAt: true, name: true, email: true }
  })
  if (!user?.onboardingCompletedAt) redirect('/onboarding')

  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')

  const assets = await prisma.materialAsset.findMany({
    where: { companyId: company.id },
    orderBy: { createdAt: 'desc' },
    select: { id: true, name: true, category: true, fileUrl: true }
  })

  const projects = await getAccessibleProjects(userId)

  return (
    <AppShell title="Materials" subtitle="資料カタログと CSV / メール" projects={projects}>
      {isGm ? (
        <section className="mb-8 space-y-3 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
          <h2 className="text-sm font-semibold text-zinc-900">GM: 資料を追加</h2>
          <form action={addMaterialAsset} className="grid gap-2 md:grid-cols-2">
            <input name="name" required placeholder="名称" className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" />
            <input name="category" placeholder="カテゴリ" className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" />
            <input
              name="fileUrl"
              required
              placeholder="https://... PDF URL"
              className="md:col-span-2 rounded-lg border border-zinc-200 px-3 py-2 text-sm"
            />
            <button
              type="submit"
              className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
            >
              追加
            </button>
          </form>
        </section>
      ) : null}

      <MaterialExportPanel assets={assets} isGm={isGm} />
    </AppShell>
  )
}
