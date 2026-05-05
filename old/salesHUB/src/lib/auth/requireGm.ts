import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'

/**
 * Requires CompanyMember gm; returns userId and company.
 */
export const requireGm = async () => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const ok = await hasCompanyRole(userId, company.id, 'gm')
  if (!ok) redirect('/')

  return { session, userId, company }
}
