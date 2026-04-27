import { describe, expect, it } from 'vitest'
import { parseListCsv } from '@/lib/lists/csvImport'

describe('parseListCsv', () => {
  it('parses header and dedupes URL within file', () => {
    const csv = [
      '会社名,電話番号,住所,企業url,業種',
      'A社,03-1,東京都,https://a.example.com,X',
      'B社,03-2,東京都,https://b.example.com,Y',
      'dup,03-3,東京都,https://a.example.com,Z'
    ].join('\n')

    const rows = parseListCsv(csv)
    expect(rows).toHaveLength(2)
    expect(rows[0]?.targetUrl).toBe('https://a.example.com')
    expect(rows[1]?.companyName).toBe('B社')
  })
})
