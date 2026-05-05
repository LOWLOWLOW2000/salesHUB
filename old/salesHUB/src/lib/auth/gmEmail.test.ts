import { describe, expect, it, vi } from 'vitest'
import { isGmEmail } from '@/lib/auth/gmEmail'

describe('gmEmail', () => {
  it('detects GM email via env', () => {
    vi.stubEnv('GM_EMAIL', 'boss@example.com')
    expect(isGmEmail('boss@example.com')).toBe(true)
    expect(isGmEmail('  BOSS@EXAMPLE.COM  ')).toBe(true)
    expect(isGmEmail('director@example.com')).toBe(false)
  })
})
