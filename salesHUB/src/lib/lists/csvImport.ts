import { normalizeCompanyName, normalizePhone, createClientRowId } from '@/lib/accounts/identity'

export type ParsedListRow = {
  companyName: string
  phone: string
  address: string
  targetUrl: string
  industryTag: string
  nameNorm: string
  phoneNorm: string
  clientRowId: string
  /** PJシートの lead_id（例: PEAK-000001）。列が存在しない場合は空文字 */
  leadId: string
}

const getIndex = (headers: string[], aliases: string[], fallback: number) => {
  const lower = headers.map((h) => h.toLowerCase())
  const idx = lower.findIndex((h) => aliases.some((a) => h === a.toLowerCase()))
  return idx >= 0 ? idx : fallback
}

/**
 * Parses CSV text into rows; skips empty lines and header.
 */
export const parseListCsv = (raw: string): ParsedListRow[] => {
  const lines = raw
    .split(/\r?\n/g)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)

  if (lines.length === 0) return []

  const headerLine = lines[0]
  const headers = headerLine.split(',').map((h) => h.trim().replace(/^"|"$/g, ''))

  const companyNameIndex = getIndex(headers, ['company', 'companyname', '会社名', '企業名'], 0)
  const phoneIndex = getIndex(headers, ['phone', 'tel', 'phonenumber', '電話番号'], 1)
  const addressIndex = getIndex(headers, ['address', '住所'], 2)
  const targetUrlIndex = getIndex(headers, ['url', 'website', 'targeturl', '企業url', 'hp'], 3)
  const industryIndex = getIndex(headers, ['industry', 'industrytag', '業種', '事業タグ'], 4)
  const leadIdIndex = getIndex(headers, ['lead_id', 'leadid'], -1)

  const dataLines = lines.slice(1)
  const urlSeen = new Set<string>()
  const out: ParsedListRow[] = []

  for (const line of dataLines) {
    const cells = line.split(',').map((c) => c.trim().replace(/^"|"$/g, ''))
    const companyName = cells[companyNameIndex] ?? ''
    const phone = cells[phoneIndex] ?? ''
    const address = cells[addressIndex] ?? ''
    const targetUrl = cells[targetUrlIndex] ?? ''
    const industryTag = cells[industryIndex] ?? ''

    if (targetUrl.length === 0) continue
    if (urlSeen.has(targetUrl)) continue
    urlSeen.add(targetUrl)

    const nameNorm = normalizeCompanyName(companyName)
    const phoneNorm = normalizePhone(phone)
    const clientRowId = createClientRowId(nameNorm, phoneNorm)
    const leadId = leadIdIndex >= 0 ? (cells[leadIdIndex] ?? '').trim() : ''

    out.push({
      companyName,
      phone,
      address,
      targetUrl,
      industryTag,
      nameNorm,
      phoneNorm,
      clientRowId,
      leadId
    })
  }

  return out
}
