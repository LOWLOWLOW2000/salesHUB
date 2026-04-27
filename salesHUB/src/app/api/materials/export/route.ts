import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'

const csvEscape = (value: string) => {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

/**
 * CSV of selected material assets (`?ids=id1,id2`) for merge / manual send.
 */
export const GET = async (req: Request) => {
  const session = await getSession()
  if (!session?.user?.id) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const url = new URL(req.url)
  const ids = (url.searchParams.get('ids') ?? '')
    .split(',')
    .map((s) => s.trim())
    .filter((s) => s.length > 0)

  if (ids.length === 0) return NextResponse.json({ error: 'ids_required' }, { status: 400 })

  const company = await getOrCreateDefaultCompany()

  const assets = await prisma.materialAsset.findMany({
    where: { id: { in: ids }, companyId: company.id },
    select: { id: true, name: true, fileUrl: true, category: true }
  })

  const header = ['id', 'name', 'category', 'fileUrl']
  const lines = assets.map((a) =>
    [a.id, a.name, a.category, a.fileUrl].map((c) => csvEscape(String(c))).join(',')
  )

  const csv = [header.join(','), ...lines].join('\n')

  return new NextResponse(csv, {
    headers: {
      'content-type': 'text/csv; charset=utf-8',
      'content-disposition': 'attachment; filename="materials-selection.csv"'
    }
  })
}
