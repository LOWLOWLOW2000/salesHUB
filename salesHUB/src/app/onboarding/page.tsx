import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import { OnboardingWizard } from '@/app/onboarding/wizard'

export default async function OnboardingPage() {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const user = await prisma.user.findUnique({
    where: { id: userId },
    select: { onboardingCompletedAt: true }
  })

  if (user?.onboardingCompletedAt) redirect('/')

  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')

  return <OnboardingWizard isGm={isGm} />
}
