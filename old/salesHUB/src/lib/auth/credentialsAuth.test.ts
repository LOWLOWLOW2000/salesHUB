import { describe, expect, it, vi, beforeEach } from 'vitest'
import { hashPassword } from '@/lib/auth/password'
import { prisma } from '@/lib/db/prisma'
import { authenticateWithCredentials } from '@/lib/auth/credentialsAuth'

vi.mock('@/lib/db/prisma', () => ({
  prisma: {
    user: {
      findUnique: vi.fn()
    }
  }
}))

describe('authenticateWithCredentials', () => {
  beforeEach(() => {
    vi.mocked(prisma.user.findUnique).mockReset()
  })

  it('returns user when password matches', async () => {
    const passwordHash = await hashPassword('ok-pass')
    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'user-1',
      email: 'a@example.com',
      name: 'Alice',
      image: null,
      passwordHash
    })

    const user = await authenticateWithCredentials('a@example.com', 'ok-pass')
    expect(user).toEqual({
      id: 'user-1',
      email: 'a@example.com',
      name: 'Alice',
      image: null
    })
  })

  it('returns null when user missing', async () => {
    vi.mocked(prisma.user.findUnique).mockResolvedValue(null)
    expect(await authenticateWithCredentials('x@y.com', 'p')).toBeNull()
  })

  it('returns null when no passwordHash', async () => {
    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'u',
      email: 'a@b.com',
      name: null,
      image: null,
      passwordHash: null
    })
    expect(await authenticateWithCredentials('a@b.com', 'p')).toBeNull()
  })

  it('returns null when password wrong', async () => {
    const passwordHash = await hashPassword('real')
    vi.mocked(prisma.user.findUnique).mockResolvedValue({
      id: 'u',
      email: 'a@b.com',
      name: null,
      image: null,
      passwordHash
    })
    expect(await authenticateWithCredentials('a@b.com', 'wrong')).toBeNull()
  })
})
