import { prisma } from '@/lib/db/prisma'

const defaultCompanyName = 'Sales Consulting'

/**
 * 部署（Company）のデフォルトを返す
 *
 * - 部署データを1つに集約し、案件はProjectとしてぶら下げる前提
 */
export const getOrCreateDefaultCompany = async () =>
  prisma.company.upsert({
    where: { name: defaultCompanyName },
    update: {},
    create: { name: defaultCompanyName },
    select: { id: true, name: true }
  })

