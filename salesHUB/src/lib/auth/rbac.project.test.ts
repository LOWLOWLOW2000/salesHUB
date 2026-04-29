import { beforeEach, describe, expect, it, vi } from 'vitest'

const companyMemberFindFirst = vi.fn()
const projectMemberFindFirst = vi.fn()

vi.mock('@/lib/db/prisma', () => ({
  prisma: {
    companyMember: { findFirst: (...args: unknown[]) => companyMemberFindFirst(...args) },
    projectMember: { findFirst: (...args: unknown[]) => projectMemberFindFirst(...args) }
  }
}))

vi.mock('@/lib/auth/company', () => ({
  getOrCreateDefaultCompany: vi.fn(() => Promise.resolve({ id: 'company-1', name: 'Sales Consulting' }))
}))

describe('canOperateProject', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('allows GM without project membership', async () => {
    companyMemberFindFirst.mockImplementation(({ where }: { where: { role?: string } }) =>
      where.role === 'gm' ? Promise.resolve({ id: 'cm-gm' }) : Promise.resolve(null)
    )
    projectMemberFindFirst.mockResolvedValue(null)

    const { canOperateProject } = await import('@/lib/auth/rbac')
    await expect(canOperateProject('user-1', 'proj-a')).resolves.toBe(true)
  })

  it('allows non-GM when they have any ProjectMember row', async () => {
    companyMemberFindFirst.mockResolvedValue(null)
    projectMemberFindFirst.mockResolvedValue({ id: 'pm-1' })

    const { canOperateProject } = await import('@/lib/auth/rbac')
    await expect(canOperateProject('user-2', 'proj-b')).resolves.toBe(true)
  })

  it('denies non-GM without project membership', async () => {
    companyMemberFindFirst.mockResolvedValue(null)
    projectMemberFindFirst.mockResolvedValue(null)

    const { canOperateProject } = await import('@/lib/auth/rbac')
    await expect(canOperateProject('user-3', 'proj-c')).resolves.toBe(false)
  })
})

describe('canConfigureProject', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('allows GM without director/as on project', async () => {
    companyMemberFindFirst.mockImplementation(({ where }: { where: { role?: string } }) =>
      where.role === 'gm' ? Promise.resolve({ id: 'cm-gm' }) : Promise.resolve(null)
    )
    projectMemberFindFirst.mockResolvedValue(null)

    const { canConfigureProject } = await import('@/lib/auth/rbac')
    await expect(canConfigureProject('user-1', 'proj-a')).resolves.toBe(true)
  })

  it('allows director on project without GM', async () => {
    companyMemberFindFirst.mockResolvedValue(null)
    projectMemberFindFirst.mockImplementation(({ where }: { where: { role?: { in?: string[] } } }) => {
      const roles = where.role?.in
      if (roles?.includes('director') || roles?.includes('as')) {
        return Promise.resolve({ id: 'pm-dir' })
      }
      return Promise.resolve(null)
    })

    const { canConfigureProject } = await import('@/lib/auth/rbac')
    await expect(canConfigureProject('user-4', 'proj-d')).resolves.toBe(true)
  })

  it('denies IS member without GM or director/as', async () => {
    companyMemberFindFirst.mockResolvedValue(null)
    projectMemberFindFirst.mockResolvedValue(null)

    const { canConfigureProject } = await import('@/lib/auth/rbac')
    await expect(canConfigureProject('user-5', 'proj-e')).resolves.toBe(false)
  })
})

describe('hasProjectMembership', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('is true when any project member row exists', async () => {
    projectMemberFindFirst.mockResolvedValue({ id: 'pm-any' })

    const { hasProjectMembership } = await import('@/lib/auth/rbac')
    await expect(hasProjectMembership('u', 'p')).resolves.toBe(true)
    expect(projectMemberFindFirst).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { userId: 'u', projectId: 'p' }
      })
    )
  })
})
