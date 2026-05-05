import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'

type DedupBody = {
  /** デdup対象のハウスリストID */
  houseListId: string
}

/**
 * POST /api/lists/dedup
 * PJシート（project_sheet）に含まれる accountId と同じものを
 * ハウスリストから削除する（ハウスリスト側が重複として削除される）。
 */
export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const body = (await req.json().catch(() => ({}))) as DedupBody
  const { houseListId } = body

  if (!houseListId?.trim()) {
    return NextResponse.json({ error: 'houseListId is required' }, { status: 400 })
  }

  const company = await getOrCreateDefaultCompany()

  // 対象のハウスリストが同 company に属するか確認
  const houseList = await prisma.masterList.findFirst({
    where: { id: houseListId.trim(), companyId: company.id, listType: 'house_list' },
    select: { id: true }
  })
  if (!houseList) {
    return NextResponse.json({ error: 'house_list_not_found' }, { status: 404 })
  }

  // 同 company の全 project_sheet アイテムの accountId を収集
  const projectSheetItems = await prisma.masterListItem.findMany({
    where: {
      masterList: { companyId: company.id, listType: 'project_sheet' }
    },
    select: { accountId: true }
  })

  const projectAccountIds = [...new Set(projectSheetItems.map((i) => i.accountId))]

  if (projectAccountIds.length === 0) {
    return NextResponse.json({ ok: true, removed: 0, message: 'no_project_sheet_data' })
  }

  // ハウスリスト内で重複している行を削除
  const { count: removed } = await prisma.masterListItem.deleteMany({
    where: {
      masterListId: houseListId.trim(),
      accountId: { in: projectAccountIds }
    }
  })

  return NextResponse.json({ ok: true, removed })
}
