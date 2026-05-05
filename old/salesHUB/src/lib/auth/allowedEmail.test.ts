import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/db/prisma', () => {
  const findUnique = vi.fn()
  return { prisma: { allowedEmail: { findUnique } } }
})

describe('allowed email', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('denies empty', async () => {
    const { prisma } = await import('@/lib/db/prisma')
    const { isEmailAllowed } = await import('@/lib/auth/allowedEmail')
    const findUnique = prisma.allowedEmail.findUnique as unknown as ReturnType<typeof vi.fn>

    await expect(isEmailAllowed('')).resolves.toBe(false)
    expect(findUnique).not.toHaveBeenCalled()
  })

  it('normalizes and checks db', async () => {
    const { prisma } = await import('@/lib/db/prisma')
    const { isEmailAllowed } = await import('@/lib/auth/allowedEmail')
    const findUnique = prisma.allowedEmail.findUnique as unknown as ReturnType<typeof vi.fn>

    findUnique.mockResolvedValue({ id: '1' })
    const result = await isEmailAllowed('  Tarou.Work363@GMAIL.com  ')
    expect(findUnique).toHaveBeenCalledTimes(1)
    expect(result).toBe(true)

    expect(findUnique).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { email: 'tarou.work363@gmail.com' }
      })
    )
  })
})

