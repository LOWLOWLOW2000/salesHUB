import { prisma } from '@/lib/db/prisma'

const DEFAULT_COMPANY_NAME = 'Sales Consulting'

/**
 * Single default tenant company (multi-tenant ready via companyId on rows).
 */
export const getOrCreateDefaultCompany = async () =>
  prisma.company.upsert({
    where: { name: DEFAULT_COMPANY_NAME },
    update: {},
    create: { name: DEFAULT_COMPANY_NAME },
    select: { id: true, name: true }
  })
