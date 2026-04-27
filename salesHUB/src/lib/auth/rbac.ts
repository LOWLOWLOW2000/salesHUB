import { prisma } from '@/lib/db/prisma'
import type { AppRole } from '@prisma/client'

/**
 * Ensures user has CompanyMember gm for the company.
 */
export const ensureGmRole = async (userId: string, companyId: string) =>
  prisma.companyMember.upsert({
    where: {
      companyId_userId_role: {
        companyId,
        userId,
        role: 'gm'
      }
    },
    update: {},
    create: {
      companyId,
      userId,
      role: 'gm'
    },
    select: { id: true }
  })

export const hasCompanyRole = async (userId: string, companyId: string, role: AppRole) => {
  const found = await prisma.companyMember.findFirst({
    where: { userId, companyId, role },
    select: { id: true }
  })
  return Boolean(found)
}

/** gm | director | as at company scope */
export const hasCompanyMgmtRole = async (userId: string, companyId: string) => {
  const found = await prisma.companyMember.findFirst({
    where: {
      userId,
      companyId,
      role: { in: ['gm', 'director', 'as'] }
    },
    select: { id: true }
  })
  return Boolean(found)
}

export const hasProjectMgmtRole = async (userId: string, projectId: string) => {
  const found = await prisma.projectMember.findFirst({
    where: {
      userId,
      projectId,
      role: { in: ['director', 'as'] }
    },
    select: { id: true }
  })
  return Boolean(found)
}
