import { describe, expect, it } from 'vitest'
import { hashPassword, verifyPassword } from '@/lib/auth/password'

describe('password', () => {
  it('hashes and verifies matching password', async () => {
    const hash = await hashPassword('correct-horse-battery')
    expect(await verifyPassword('correct-horse-battery', hash)).toBe(true)
  })

  it('rejects wrong password', async () => {
    const hash = await hashPassword('secret-a')
    expect(await verifyPassword('secret-b', hash)).toBe(false)
  })
})
