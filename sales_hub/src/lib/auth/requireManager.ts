import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'

export const requireManager = async () => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const ok = await hasCompanyRole(userId, company.id, 'manager')
  if (!ok) redirect('/')

  return { session, company }
}

