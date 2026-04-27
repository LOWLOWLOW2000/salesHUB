import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import { parseListCsv } from '@/lib/lists/csvImport'
import { domainFromUrl } from '@/lib/accounts/identity'

const canManageList = async (userId: string, companyId: string, ownerUserId: string) => {
  if (ownerUserId === userId) return true
  if (await hasCompanyRole(userId, companyId, 'gm')) return true
  const wide = await prisma.companyMember.findFirst({
    where: {
      userId,
      companyId,
      role: { in: ['director', 'as'] }
    },
    select: { id: true }
  })
  return Boolean(wide)
}

/**
 * multipart/form-data: `file` (CSV), `listName` (new list) or `listId` (append).
 */
export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const formData = await req.formData()
  const listName = String(formData.get('listName') ?? '').trim()
  const listIdExisting = String(formData.get('listId') ?? '').trim()
  const listTypeParam = String(formData.get('listType') ?? '').trim()
  const file = formData.get('file')

  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: 'file_required' }, { status: 400 })
  }

  const text = await file.text()
  const rows = parseListCsv(text)
  if (rows.length === 0) {
    return NextResponse.json({ error: 'no_rows' }, { status: 400 })
  }

  const company = await getOrCreateDefaultCompany()

  let list =
    listIdExisting.length > 0
      ? await prisma.masterList.findFirst({
          where: { id: listIdExisting, companyId: company.id },
          select: { id: true, ownerUserId: true }
        })
      : null

  if (listIdExisting.length > 0 && !list) {
    return NextResponse.json({ error: 'list_not_found' }, { status: 404 })
  }

  if (list && !(await canManageList(userId, company.id, list.ownerUserId))) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 })
  }

  if (!list) {
    if (listName.length === 0) {
      return NextResponse.json({ error: 'listName_required' }, { status: 400 })
    }

    list = await prisma.masterList.create({
      data: {
        companyId: company.id,
        ownerUserId: userId,
        name: listName,
        listType: listTypeParam === 'project_sheet' ? 'project_sheet' : 'house_list'
      },
      select: { id: true, ownerUserId: true }
    })
  }

  let imported = 0

  for (const row of rows) {
    const account = await prisma.salesAccount.upsert({
      where: {
        companyId_clientRowId: {
          companyId: company.id,
          clientRowId: row.clientRowId
        }
      },
      create: {
        companyId: company.id,
        displayName: row.companyName,
        nameNorm: row.nameNorm,
        phoneNorm: row.phoneNorm,
        clientRowId: row.clientRowId,
        headOfficeAddress: row.address,
        domain: domainFromUrl(row.targetUrl) || undefined
      },
      update: {
        displayName: row.companyName,
        headOfficeAddress: row.address,
        domain: domainFromUrl(row.targetUrl) || undefined
      },
      select: { id: true }
    })

    await prisma.masterListItem.create({
      data: {
        masterListId: list.id,
        accountId: account.id,
        companyName: row.companyName,
        phone: row.phone,
        address: row.address,
        targetUrl: row.targetUrl,
        status: 'new'
      }
    })

    imported += 1
  }

  return NextResponse.json({ ok: true, listId: list.id, imported })
}
