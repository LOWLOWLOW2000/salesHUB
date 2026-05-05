import Link from 'next/link'
import { prisma } from '@/lib/db/prisma'
import { requireGm } from '@/lib/auth/requireGm'

/**
 * GM-only cross-project overview (RevOps-style rollup).
 */
export default async function CompanyOverviewPage() {
  const { company } = await requireGm()

  const projects = await prisma.project.findMany({
    where: { companyId: company.id },
    select: { id: true, name: true }
  })

  const projectIds = projects.map((p) => p.id)

  const callAgg = await prisma.callLog.groupBy({
    by: ['result'],
    where: { projectId: { in: projectIds } },
    _count: { id: true }
  })

  const dealAgg = await prisma.dealStage.groupBy({
    by: ['stage'],
    where: { projectId: { in: projectIds } },
    _count: { id: true }
  })

  const totalCalls = callAgg.reduce((s, r) => s + r._count.id, 0)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">GM ダッシュボード</h1>
          <p className="mt-1 text-sm text-zinc-600">全案件の架電記録・商談ステージ集計</p>
        </div>
        <Link href="/admin" className="text-sm text-zinc-700 hover:text-zinc-950">
          ← Admin
        </Link>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm">
        <div className="font-semibold text-zinc-900">CallLog 合計</div>
        <div className="mt-1 text-2xl font-bold text-zinc-950">{totalCalls}</div>
        <ul className="mt-3 space-y-1 text-zinc-700">
          {callAgg.map((row) => (
            <li key={row.result} className="flex justify-between">
              <span>{row.result}</span>
              <span className="font-medium">{row._count.id}</span>
            </li>
          ))}
          {callAgg.length === 0 ? <li className="text-zinc-500">データなし</li> : null}
        </ul>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm">
        <div className="font-semibold text-zinc-900">DealStage 内訳</div>
        <ul className="mt-3 space-y-1 text-zinc-700">
          {dealAgg.map((row) => (
            <li key={row.stage} className="flex justify-between">
              <span>{row.stage}</span>
              <span className="font-medium">{row._count.id}</span>
            </li>
          ))}
          {dealAgg.length === 0 ? <li className="text-zinc-500">データなし</li> : null}
        </ul>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm">
        <div className="font-semibold text-zinc-900">Projects</div>
        <ul className="mt-2 space-y-1">
          {projects.map((p) => (
            <li key={p.id}>
              <Link href={`/project/${p.id}`} className="text-zinc-800 underline-offset-2 hover:underline">
                {p.name}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
