import { NextResponse } from 'next/server'
import { google } from 'googleapis'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { normalizeCompanyName, normalizePhone, createClientRowId, domainFromUrl } from '@/lib/accounts/identity'

type SyncSheetBody = {
  /** Google SpreadsheetのID（URL内の /d/<id>/） */
  spreadsheetId: string
  /** タブ名（シート名） */
  sheetName: string
  /** 既存リストに上書き同期する場合のリストID */
  listId?: string
  /** 新規作成時のリスト名 */
  listName?: string
}

/**
 * シートの先頭行をヘッダーとして、各カラムのインデックスを解決する。
 */
const resolveColumnIndices = (headers: string[]) => {
  const lower = headers.map((h) => h.toLowerCase().trim())
  const find = (aliases: string[], fallback: number) => {
    const idx = lower.findIndex((h) => aliases.some((a) => h === a))
    return idx >= 0 ? idx : fallback
  }
  return {
    companyNameIdx: find(['company', 'companyname', '会社名', '企業名'], 0),
    phoneIdx: find(['phone', 'tel', 'phonenumber', '電話番号'], 1),
    addressIdx: find(['address', '住所'], 2),
    urlIdx: find(['url', 'website', 'targeturl', '企業url', 'hp'], 3),
    industryIdx: find(['industry', 'industrytag', '業種'], 4)
  }
}

/**
 * POST /api/lists/sync-sheet
 * 指定した Google Spreadsheet のシートタブを取り込み、project_sheet リストとして保存する。
 * 既存リストを指定した場合は全アイテムを入れ替える（再同期）。
 */
export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const body = (await req.json().catch(() => ({}))) as SyncSheetBody
  const { spreadsheetId, sheetName, listId, listName } = body

  if (!spreadsheetId?.trim() || !sheetName?.trim()) {
    return NextResponse.json({ error: 'spreadsheetId and sheetName are required' }, { status: 400 })
  }

  // ユーザーの Google access_token を取得する
  const account = await prisma.account.findFirst({
    where: { userId, provider: 'google' },
    select: { access_token: true, refresh_token: true }
  })

  if (!account?.access_token) {
    return NextResponse.json({ error: 'google_token_missing' }, { status: 400 })
  }

  // googleapis クライアントをセットアップ
  const oauthClient = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
  )
  oauthClient.setCredentials({
    access_token: account.access_token,
    refresh_token: account.refresh_token ?? undefined
  })

  const sheets = google.sheets({ version: 'v4', auth: oauthClient })

  let rawRows: string[][]
  try {
    const res = await sheets.spreadsheets.values.get({
      spreadsheetId: spreadsheetId.trim(),
      range: sheetName.trim()
    })
    rawRows = (res.data.values ?? []).map((row) => row.map((cell) => String(cell ?? '').trim()))
  } catch (err) {
    const message = err instanceof Error ? err.message : 'sheets_fetch_error'
    return NextResponse.json({ error: message }, { status: 502 })
  }

  if (rawRows.length < 2) {
    return NextResponse.json({ error: 'no_data_rows' }, { status: 400 })
  }

  const [headerRow, ...dataRows] = rawRows
  const cols = resolveColumnIndices(headerRow)

  const company = await getOrCreateDefaultCompany()

  // リストを取得または新規作成
  let targetListId: string

  if (listId?.trim()) {
    const existing = await prisma.masterList.findFirst({
      where: { id: listId.trim(), companyId: company.id },
      select: { id: true }
    })
    if (!existing) return NextResponse.json({ error: 'list_not_found' }, { status: 404 })
    targetListId = existing.id

    // 再同期: 既存アイテムをすべて削除してから再投入
    await prisma.masterListItem.deleteMany({ where: { masterListId: targetListId } })
  } else {
    const name = listName?.trim() ?? sheetName.trim()
    const created = await prisma.masterList.create({
      data: {
        companyId: company.id,
        ownerUserId: userId,
        name,
        listType: 'project_sheet',
        googleSpreadsheetId: spreadsheetId.trim(),
        googleSheetName: sheetName.trim()
      },
      select: { id: true }
    })
    targetListId = created.id
  }

  // シートのメタ情報を更新
  await prisma.masterList.update({
    where: { id: targetListId },
    data: {
      listType: 'project_sheet',
      googleSpreadsheetId: spreadsheetId.trim(),
      googleSheetName: sheetName.trim(),
      lastSyncedAt: new Date()
    }
  })

  let imported = 0
  const urlSeen = new Set<string>()

  for (const row of dataRows) {
    const companyName = row[cols.companyNameIdx] ?? ''
    const phone = row[cols.phoneIdx] ?? ''
    const address = row[cols.addressIdx] ?? ''
    const targetUrl = row[cols.urlIdx] ?? ''

    if (targetUrl.length === 0) continue
    if (urlSeen.has(targetUrl)) continue
    urlSeen.add(targetUrl)

    const nameNorm = normalizeCompanyName(companyName)
    const phoneNorm = normalizePhone(phone)
    const clientRowId = createClientRowId(nameNorm, phoneNorm)

    const account = await prisma.salesAccount.upsert({
      where: { companyId_clientRowId: { companyId: company.id, clientRowId } },
      create: {
        companyId: company.id,
        displayName: companyName,
        nameNorm,
        phoneNorm,
        clientRowId,
        headOfficeAddress: address,
        domain: domainFromUrl(targetUrl) || undefined
      },
      update: {
        displayName: companyName,
        headOfficeAddress: address,
        domain: domainFromUrl(targetUrl) || undefined
      },
      select: { id: true }
    })

    await prisma.masterListItem.create({
      data: {
        masterListId: targetListId,
        accountId: account.id,
        companyName,
        phone,
        address,
        targetUrl,
        status: 'new'
      }
    })

    imported += 1
  }

  return NextResponse.json({ ok: true, listId: targetListId, imported })
}
