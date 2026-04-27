import { describe, expect, it, vi } from 'vitest'
import { isManagerEmail } from '@/lib/auth/managerEmail'

describe('rbac', () => {
  it('detects manager email via env', () => {
    vi.stubEnv('MANAGER_EMAIL', 'boss@example.com')
    expect(isManagerEmail('boss@example.com')).toBe(true)
    expect(isManagerEmail('  BOSS@EXAMPLE.COM  ')).toBe(true)
    expect(isManagerEmail('director@example.com')).toBe(false)
  })
})

