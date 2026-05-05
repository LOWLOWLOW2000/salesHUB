import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import type { AppRole } from '@prisma/client'

const rolePriority: AppRole[] = ['gm', 'manager', 'director', 'leader', 'as', 'is', 'fs', 'cs']

const roleBadgeLabel = (role: AppRole | null) =>
  (
    {
      gm: 'GM',
      manager: 'MANAGER',
      director: 'DIRECTOR',
      leader: 'LEADER',
      as: 'AS',
      is: 'IS',
      fs: 'FS',
      cs: 'CS'
    } satisfies Record<AppRole, string>
  )[role ?? 'is'] ?? 'MEMBER'

export type SidebarProfile = {
  displayName: string
  email: string
  roleLabel: string
}

/**
 * Returns compact profile data for sidebar header.
 */
export const getSidebarProfile = async (userId: string): Promise<SidebarProfile | null> => {
  const company = await getOrCreateDefaultCompany()
  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: {
      name: true,
      email: true,
      companyMembers: {
        where: { companyId: company.id },
        select: { role: true }
      }
    }
  })

  if (!user?.email) return null

  const role = rolePriority.find((candidate) => user.companyMembers.some((member) => member.role === candidate)) ?? null

  return {
    displayName: (user.name ?? '').trim(),
    email: user.email,
    roleLabel: roleBadgeLabel(role)
  }
}
