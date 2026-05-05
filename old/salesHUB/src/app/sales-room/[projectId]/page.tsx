import Link from 'next/link'
import { redirect, notFound } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getProjectCapabilityFlags } from '@/lib/auth/projectCapabilities'
import { canAccessProject } from '@/lib/projects/accessibleProjects'
import { AppShell } from '@/app/_components/AppShell'
import { getAccessibleProjects } from '@/lib/projects/accessibleProjects'
import { SalesRoomClient } from '@/app/_components/sales-room/SalesRoomClient'
import { getSidebarProfile } from '@/lib/auth/sidebarProfile'

type Props = {
  params: Promise<{ projectId: string }>
  searchParams: Promise<{ listId?: string | string[] }>
}

export default async function SalesRoomPage({ params, searchParams }: Props) {
  const { projectId } = await params
  const sp = await searchParams
  const listIdRaw = Array.isArray(sp.listId) ? sp.listId[0] : sp.listId
  const listId = listIdRaw?.trim() ?? ''

  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  if (!(await canAccessProject(userId, projectId))) redirect('/')

  if (listId.length === 0) {
    return (
      <div className="space-y-4">
        <p className="text-sm text-zinc-600">クエリ <code className="rounded bg-zinc-100 px-1">listId</code> が必要です。</p>
        <Link href="/master-lists" className="text-sm text-blue-700 hover:underline">
          Master lists へ
        </Link>
      </div>
    )
  }

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    select: { name: true, companyId: true }
  })
  if (!project) notFound()

  const list = await prisma.masterList.findFirst({
    where: { id: listId, companyId: project.companyId },
    select: { id: true }
  })
  if (!list) notFound()

  const items = await prisma.masterListItem.findMany({
    where: { masterListId: list.id },
    orderBy: { createdAt: 'asc' },
    select: {
      id: true,
      companyName: true,
      phone: true,
      targetUrl: true,
      status: true
    }
  })

  const [projects, { canOperate }, profile] = await Promise.all([
    getAccessibleProjects(userId),
    getProjectCapabilityFlags(userId, projectId),
    getSidebarProfile(userId)
  ])

  return (
    <AppShell title={`架電: ${project.name}`} subtitle={`listId=${list.id}`} projects={projects} profile={profile}>
      <div className="mb-4 flex flex-wrap gap-3 text-sm">
        <Link href={`/project/${projectId}`} className="text-zinc-600 hover:text-zinc-950">
          ← Project ツール
        </Link>
        <Link href={`/master-lists/${list.id}`} className="text-zinc-600 hover:text-zinc-950">
          Master list 詳細
        </Link>
      </div>
      <SalesRoomClient projectId={projectId} listId={list.id} rows={items} canOperate={canOperate} />
    </AppShell>
  )
}
