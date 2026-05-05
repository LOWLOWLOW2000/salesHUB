import { prisma } from '@/lib/db/prisma'
import type { AppRole } from '@prisma/client'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'

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

/** gm | manager | as at company scope */
export const hasCompanyMgmtRole = async (userId: string, companyId: string) => {
  const found = await prisma.companyMember.findFirst({
    where: {
      userId,
      companyId,
      role: { in: ['gm', 'manager', 'as'] }
    },
    select: { id: true }
  })
  return Boolean(found)
}

/**
 * Project-scoped director or as (`as` は獲得案件で ProjectMember 付与されれば支配人相当の設定権に乗る想定)。
 */
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

/** Any `ProjectMember` on the project (field / director / as). */
export const hasProjectMembership = async (userId: string, projectId: string) => {
  const found = await prisma.projectMember.findFirst({
    where: { userId, projectId },
    select: { id: true }
  })
  return Boolean(found)
}

/**
 * Scripts and other project configuration: project director/as/leader.
 */
export const hasProjectConfigureRole = async (userId: string, projectId: string) => {
  const found = await prisma.projectMember.findFirst({
    where: {
      userId,
      projectId,
      role: { in: ['director', 'as', 'leader'] }
    },
    select: { id: true }
  })
  return Boolean(found)
}

/** Scripts and other project configuration: GM or project director/as. */
export const canConfigureProject = async (userId: string, projectId: string) => {
  const company = await getOrCreateDefaultCompany()
  if (await hasCompanyRole(userId, company.id, 'gm')) return true
  return hasProjectConfigureRole(userId, projectId)
}

/** Call logs, daily reports, dial, etc.: GM or any project member. */
export const canOperateProject = async (userId: string, projectId: string) => {
  const company = await getOrCreateDefaultCompany()
  if (await hasCompanyRole(userId, company.id, 'gm')) return true
  return hasProjectMembership(userId, projectId)
}
