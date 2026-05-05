import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/auth/company', () => ({
  getOrCreateDefaultCompany: vi.fn(() =>
    Promise.resolve({ id: 'company-1', name: 'Sales Consulting' })
  )
}))

const hasCompanyRole = vi.fn()
const companyMemberFindFirst = vi.fn()

vi.mock('@/lib/auth/rbac', () => ({
  hasCompanyRole: (...args: unknown[]) => hasCompanyRole(...args)
}))

const findMany = vi.fn()

vi.mock('@/lib/db/prisma', () => ({
  prisma: {
    companyMember: { findFirst: (...args: unknown[]) => companyMemberFindFirst(...args) },
    project: { findMany }
  }
}))

describe('getAccessibleProjects', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('loads all company projects when user is gm', async () => {
    hasCompanyRole.mockImplementation(async (_u, _c, role: string) => role === 'gm')
    companyMemberFindFirst.mockResolvedValue(null)
    findMany.mockResolvedValue([
      { id: 'p1', name: 'Alpha' },
      { id: 'p2', name: 'Beta' }
    ])

    const { getAccessibleProjects } = await import('@/lib/projects/accessibleProjects')
    const rows = await getAccessibleProjects('user-1')

    expect(hasCompanyRole).toHaveBeenCalledWith('user-1', 'company-1', 'gm')
    expect(rows).toEqual([
      { id: 'p1', name: 'Alpha' },
      { id: 'p2', name: 'Beta' }
    ])
  })

  it('loads all company projects when user has company manager/as', async () => {
    hasCompanyRole.mockResolvedValue(false)
    companyMemberFindFirst.mockResolvedValue({ id: 'cm-1' })
    findMany.mockResolvedValue([{ id: 'p1', name: 'Alpha' }])

    const { getAccessibleProjects } = await import('@/lib/projects/accessibleProjects')
    const rows = await getAccessibleProjects('user-2')

    expect(companyMemberFindFirst).toHaveBeenCalled()
    expect(rows).toEqual([{ id: 'p1', name: 'Alpha' }])
  })

  it('loads only member projects otherwise', async () => {
    hasCompanyRole.mockResolvedValue(false)
    companyMemberFindFirst.mockResolvedValue(null)
    findMany.mockResolvedValue([{ id: 'p9', name: 'Solo' }])

    const { getAccessibleProjects } = await import('@/lib/projects/accessibleProjects')
    const rows = await getAccessibleProjects('user-3')

    expect(findMany).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { members: { some: { userId: 'user-3' } } },
        orderBy: { name: 'asc' },
        select: { id: true, name: true }
      })
    )
    expect(rows).toEqual([{ id: 'p9', name: 'Solo' }])
  })
})

describe('canAccessProject', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns true when project is in accessible list', async () => {
    hasCompanyRole.mockResolvedValue(false)
    companyMemberFindFirst.mockResolvedValue(null)
    findMany.mockResolvedValue([{ id: 'p9', name: 'Solo' }])

    const { canAccessProject } = await import('@/lib/projects/accessibleProjects')
    await expect(canAccessProject('user-2', 'p9')).resolves.toBe(true)
    await expect(canAccessProject('user-2', 'other')).resolves.toBe(false)
  })
})
