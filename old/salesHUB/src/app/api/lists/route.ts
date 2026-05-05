import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'

/**
 * GET /api/lists
 * 全 MasterList（PJシート + ハウスリスト）をアイテム件数付きで返す。
 */
export const GET = async () => {
  const session = await getSession()
  if (!session?.user?.id) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const company = await getOrCreateDefaultCompany()

  const lists = await prisma.masterList.findMany({
    where: { companyId: company.id },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      name: true,
      listType: true,
      googleSpreadsheetId: true,
      googleSheetName: true,
      lastSyncedAt: true,
      createdAt: true,
      _count: { select: { items: true } }
    }
  })

  const projectSheetCount = lists
    .filter((l) => l.listType === 'project_sheet')
    .reduce((sum, l) => sum + l._count.items, 0)

  const houseListCount = lists
    .filter((l) => l.listType === 'house_list')
    .reduce((sum, l) => sum + l._count.items, 0)

  return NextResponse.json({
    lists,
    kpi: {
      projectSheetCount,
      houseListCount,
      totalCount: projectSheetCount + houseListCount
    }
  })
}
