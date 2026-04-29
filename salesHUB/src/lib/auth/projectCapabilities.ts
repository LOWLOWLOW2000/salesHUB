import { canConfigureProject, canOperateProject } from '@/lib/auth/rbac'

export type ProjectCapabilityFlags = {
  canOperate: boolean
  canConfigure: boolean
}

/**
 * Single fetch of project-scoped RBAC for UI (avoid duplicate DB round-trips per tool).
 */
export const getProjectCapabilityFlags = async (
  userId: string,
  projectId: string
): Promise<ProjectCapabilityFlags> => {
  const [canOperate, canConfigure] = await Promise.all([
    canOperateProject(userId, projectId),
    canConfigureProject(userId, projectId)
  ])
  return { canOperate, canConfigure }
}
