import { describe, expect, it } from 'vitest'
import { createClientRowId, normalizeCompanyName, normalizePhone } from '@/lib/accounts/identity'

describe('identity', () => {
  it('normalizes company name and phone', () => {
    expect(normalizeCompanyName('  Foo   Bar  ')).toBe('Foo Bar')
    expect(normalizePhone('03-1234-5678')).toBe('0312345678')
  })

  it('creates stable clientRowId', () => {
    const a = createClientRowId('Acme', '09012345678')
    const b = createClientRowId('Acme', '09012345678')
    const c = createClientRowId('Acme Corp', '09012345678')
    expect(a).toMatch(/^cr_[0-9a-f]{16}$/)
    expect(a).toBe(b)
    expect(a).not.toBe(c)
  })
})
