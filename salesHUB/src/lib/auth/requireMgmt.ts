import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyMgmtRole, hasCompanyRole, hasProjectMgmtRole } from '@/lib/auth/rbac'

/**
 * Company-level management (gm | director | as on CompanyMember).
 */
export const requireCompanyMgmt = async () => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const ok = await hasCompanyMgmtRole(userId, company.id)
  if (!ok) redirect('/')

  return { userId, company }
}

/**
 * Project-level director/as OR global gm.
 */
export const requireProjectMgmt = async (projectId: string) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')
  if (isGm) return { userId, company }

  const ok = await hasProjectMgmtRole(userId, projectId)
  if (!ok) redirect('/')

  return { userId, company }
}
