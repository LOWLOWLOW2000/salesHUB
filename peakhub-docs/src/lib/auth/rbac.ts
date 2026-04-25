import { prisma } from '@/lib/db/prisma'
import type { AppRole } from '@prisma/client'

export const ensureManagerRole = async (userId: string, companyId: string) =>
  prisma.companyMember.upsert({
    where: {
      companyId_userId_role: {
        companyId,
        userId,
        role: 'manager'
      }
    },
    update: {},
    create: {
      companyId,
      userId,
      role: 'manager'
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

