import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'

export type AccessibleProject = {
  id: string
  name: string
}

/**
 * Projects the user may open (gm/manager/as: all company projects; others: ProjectMember only).
 */
export const getAccessibleProjects = async (userId: string): Promise<AccessibleProject[]> => {
  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')
  const hasWideCompanyAccess = await prisma.companyMember.findFirst({
    where: {
      userId,
      companyId: company.id,
      role: { in: ['manager', 'as'] }
    },
    select: { id: true }
  })

  if (isGm || hasWideCompanyAccess) {
    return prisma.project.findMany({
      where: { companyId: company.id },
      orderBy: { name: 'asc' },
      select: { id: true, name: true }
    })
  }

  return prisma.project.findMany({
    where: { members: { some: { userId } } },
    orderBy: { name: 'asc' },
    select: { id: true, name: true }
  })
}

/**
 * Whether the user may view / open a project (nav, read APIs, KPI AI save, etc.).
 */
export const canViewProject = async (userId: string, projectId: string): Promise<boolean> => {
  const projects = await getAccessibleProjects(userId)
  return projects.some((p) => p.id === projectId)
}

/**
 * Back-compat alias of {@link canViewProject}.
 */
export const canAccessProject = canViewProject
