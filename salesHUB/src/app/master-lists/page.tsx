import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { MasterListsClient, type MasterListSummary } from './MasterListsClient'
import type { MasterListItemStatus } from '@prisma/client'

export const metadata = { title: 'Master Lists' }

const fetchListsWithItems = async (companyId: string) => {
  const lists = await prisma.masterList.findMany({
    where: { companyId },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      name: true,
      listType: true,
      googleSpreadsheetId: true,
      googleSheetName: true,
      lastSyncedAt: true,
      createdAt: true,
      items: {
        orderBy: { createdAt: 'asc' },
        select: {
          id: true,
          companyName: true,
          phone: true,
          address: true,
          targetUrl: true,
          status: true,
          lastResult: true
        }
      }
    }
  })

  return lists.map((list) => ({
    id: list.id,
    name: list.name,
    listType: list.listType as 'project_sheet' | 'house_list',
    googleSpreadsheetId: list.googleSpreadsheetId,
    googleSheetName: list.googleSheetName,
    lastSyncedAt: list.lastSyncedAt?.toISOString() ?? null,
    createdAt: list.createdAt.toISOString(),
    itemCount: list.items.length,
    items: list.items.map((item) => ({
      id: item.id,
      companyName: item.companyName,
      phone: item.phone,
      address: item.address,
      targetUrl: item.targetUrl,
      status: item.status as MasterListItemStatus,
      lastResult: item.lastResult
    }))
  })) satisfies MasterListSummary[]
}

export default async function MasterListsPage() {
  const session = await getSession()
  if (!session?.user?.id) redirect('/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const allLists = await fetchListsWithItems(company.id)

  const projectSheetLists = allLists.filter((l) => l.listType === 'project_sheet')
  const houseListLists = allLists.filter((l) => l.listType === 'house_list')

  const kpi = {
    projectSheetCount: projectSheetLists.reduce((sum, l) => sum + l.itemCount, 0),
    houseListCount: houseListLists.reduce((sum, l) => sum + l.itemCount, 0),
    totalCount: allLists.reduce((sum, l) => sum + l.itemCount, 0)
  }

  return (
    <div className="space-y-4">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Master Lists</h1>
        <p className="text-sm text-zinc-600">
          PJシート（Google Spreadsheet 連携）とハウスリスト（CSV取込）を管理します
        </p>
      </div>

      <MasterListsClient
        projectSheetLists={projectSheetLists}
        houseListLists={houseListLists}
        kpi={kpi}
      />
    </div>
  )
}
