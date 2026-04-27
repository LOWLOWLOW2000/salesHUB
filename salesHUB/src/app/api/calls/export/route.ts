import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { canAccessProject } from '@/lib/projects/accessibleProjects'

const csvEscape = (value: string) => {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * CSV export of CallLog for a project (GET `?projectId=`).
 */
export const GET = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const url = new URL(req.url)
  const projectId = url.searchParams.get('projectId') ?? ''
  if (projectId.length === 0) return NextResponse.json({ error: 'projectId_required' }, { status: 400 })

  if (!(await canAccessProject(userId, projectId))) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 })
  }

  const logs = await prisma.callLog.findMany({
    where: { projectId },
    orderBy: { startedAt: 'desc' },
    take: 10_000,
    include: {
      user: { select: { email: true } },
      account: { select: { displayName: true, clientRowId: true } }
    }
  })

  const header = ['startedAt', 'userEmail', 'result', 'memo', 'accountName', 'clientRowId', 'accountId']
  const lines = logs.map((log) =>
    [
      log.startedAt.toISOString(),
      log.user.email ?? '',
      log.result,
      log.memo,
      log.account.displayName,
      log.account.clientRowId,
      log.accountId
    ]
      .map((c) => csvEscape(String(c)))
      .join(',')
  )

  const csv = [header.join(','), ...lines].join('\n')

  return new NextResponse(csv, {
    headers: {
      'content-type': 'text/csv; charset=utf-8',
      'content-disposition': `attachment; filename="calls-${projectId}.csv"`
    }
  })
}
