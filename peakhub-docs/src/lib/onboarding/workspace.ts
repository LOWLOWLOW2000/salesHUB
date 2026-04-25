import { prisma } from '@/lib/db/prisma'
import type { WorkspaceRole, WorkspaceType } from '@prisma/client'

const is01WorkspaceName = 'IS01'

/**
 * IS01管理の自動部隊ワークスペースを返す
 */
export const getOrCreateIs01Workspace = async () =>
  prisma.workspace.upsert({
    where: {
      type_name: {
        type: 'auto_squad',
        name: is01WorkspaceName
      }
    },
    update: {},
    create: {
      type: 'auto_squad',
      name: is01WorkspaceName
    },
    select: { id: true, type: true, name: true }
  })

export const createClientWorkspace = async (name: string) =>
  prisma.workspace.create({
    data: { type: 'client', name },
    select: { id: true, type: true, name: true }
  })

export const upsertWorkspaceMember = async (
  workspaceId: string,
  userId: string,
  role: WorkspaceRole
) =>
  prisma.workspaceMember.upsert({
    where: { workspaceId_userId: { workspaceId, userId } },
    update: { role },
    create: { workspaceId, userId, role },
    select: { id: true }
  })

export const completeOnboarding = async (userId: string, workspaceId: string) =>
  prisma.user.update({
    where: { id: userId },
    data: {
      onboardingCompletedAt: new Date(),
      primaryWorkspaceId: workspaceId
    },
    select: { id: true }
  })

export const getUserWorkspaceState = async (userId: string) => {
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      onboardingCompletedAt: true,
      primaryWorkspaceId: true,
      workspaceRoles: {
        select: {
          workspaceId: true,
          role: true,
          workspace: { select: { type: true, name: true } }
        },
        orderBy: { createdAt: 'desc' }
      }
    }
  })

  return {
    onboardingCompleted: Boolean(user?.onboardingCompletedAt),
    primaryWorkspaceId: user?.primaryWorkspaceId ?? null,
    memberships: user?.workspaceRoles ?? []
  }
}

export const isWorkspaceType = (value: string): value is WorkspaceType =>
  value === 'client' || value === 'auto_squad'

