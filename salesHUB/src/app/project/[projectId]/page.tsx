import { Suspense } from 'react'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { AppShell } from '@/app/_components/AppShell'
import { ProjectToolWorkspace } from '@/app/_components/ProjectToolWorkspace'
import { normalizeProjectToolId } from '@/lib/projectTools/toolSections'
import { getProjectCapabilityFlags } from '@/lib/auth/projectCapabilities'
import { canAccessProject, getAccessibleProjects } from '@/lib/projects/accessibleProjects'

type Props = {
  params: Promise<{ projectId: string }>
  searchParams: Promise<{ tool?: string | string[] }>
}

export default async function ProjectDashboardPage({ params, searchParams }: Props) {
  const { projectId } = await params
  const { tool } = await searchParams
  const activeTool = normalizeProjectToolId(Array.isArray(tool) ? tool[0] : tool)
  const session = await getSession()
  const userId = session?.user?.id

  if (!userId) redirect('/auth/signin')

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { onboardingCompletedAt: true }
  })

  if (!user?.onboardingCompletedAt) redirect('/onboarding')

  const allowed = await canAccessProject(userId, projectId)
  if (!allowed) redirect('/')

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    select: { name: true }
  })

  if (!project) redirect('/')

  const [projects, capabilities] = await Promise.all([
    getAccessibleProjects(userId),
    getProjectCapabilityFlags(userId, projectId)
  ])

  return (
    <AppShell title={project.name} subtitle="プロジェクト実行ツール（左から機能を育てます）" projects={projects}>
      <Suspense
        fallback={<p className="text-sm text-zinc-600">実行ツールを読み込み中です…</p>}
      >
        <ProjectToolWorkspace projectId={projectId} activeId={activeTool} capabilities={capabilities} />
      </Suspense>
    </AppShell>
  )
}
