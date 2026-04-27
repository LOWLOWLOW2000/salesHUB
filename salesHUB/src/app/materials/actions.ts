'use server'

import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'

/**
 * GM registers a material asset (URL to PDF etc.).
 */
export const addMaterialAsset = async (formData: FormData) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/api/auth/signin')

  const company = await getOrCreateDefaultCompany()
  if (!(await hasCompanyRole(userId, company.id, 'gm'))) redirect('/')

  const name = String(formData.get('name') ?? '').trim()
  const fileUrl = String(formData.get('fileUrl') ?? '').trim()
  const category = String(formData.get('category') ?? '').trim()
  if (name.length === 0 || fileUrl.length === 0) return

  await prisma.materialAsset.create({
    data: {
      companyId: company.id,
      name,
      fileUrl,
      category
    }
  })

  revalidatePath('/materials')
}
