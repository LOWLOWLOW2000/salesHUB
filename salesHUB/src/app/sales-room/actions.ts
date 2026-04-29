'use server'

import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { canOperateProject } from '@/lib/auth/rbac'
import { isCallingResult } from '@/lib/calling/callResults'

const excludedListStatuses = new Set(['番号違い', 'クレーム'])

/**
 * Persists a call log row and syncs MasterListItem status.
 */
export const saveCallLogAction = async (formData: FormData) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const projectId = String(formData.get('projectId') ?? '')
  const masterListItemId = String(formData.get('masterListItemId') ?? '').trim()
  const result = String(formData.get('result') ?? '').trim()
  const memo = String(formData.get('memo') ?? '').trim()

  if (projectId.length === 0 || masterListItemId.length === 0) return
  if (!(await canOperateProject(userId, projectId))) redirect('/')
  if (!isCallingResult(result)) return

  const item = await prisma.masterListItem.findUnique({
    where: { id: masterListItemId },
    include: { masterList: true }
  })

  if (!item) return

  const project = await prisma.project.findUnique({
    where: { id: projectId },
    select: { companyId: true }
  })

  if (!project || project.companyId !== item.masterList.companyId) return

  await prisma.$transaction([
    prisma.callLog.create({
      data: {
        projectId,
        userId,
        accountId: item.accountId,
        masterListItemId: item.id,
        result,
        memo
      }
    }),
    prisma.masterListItem.update({
      where: { id: item.id },
      data: {
        lastResult: result,
        status: excludedListStatuses.has(result) ? 'excluded' : 'done'
      }
    })
  ])

  redirect(`/sales-room/${projectId}?listId=${encodeURIComponent(item.masterListId)}`)
}
