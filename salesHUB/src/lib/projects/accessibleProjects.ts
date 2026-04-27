import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'

export type AccessibleProject = {
  id: string
  name: string
}

/**
 * Projects the user may open (gm: all company projects; others: ProjectMember only).
 */
export const getAccessibleProjects = async (userId: string): Promise<AccessibleProject[]> => {
  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')
  const hasWideCompanyAccess = await prisma.companyMember.findFirst({
    where: {
      userId,
      companyId: company.id,
      role: { in: ['director', 'as'] }
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
 * Whether the user may access a given Project id (always validate on the server).
 */
export const canAccessProject = async (userId: string, projectId: string): Promise<boolean> => {
  const projects = await getAccessibleProjects(userId)
  return projects.some((p) => p.id === projectId)
}
