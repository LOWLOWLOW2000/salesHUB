import { beforeEach, describe, expect, it, vi } from 'vitest'

const canOperateProject = vi.fn()
const canConfigureProject = vi.fn()

vi.mock('@/lib/auth/rbac', () => ({
  canOperateProject: (...args: unknown[]) => canOperateProject(...args),
  canConfigureProject: (...args: unknown[]) => canConfigureProject(...args)
}))

describe('getProjectCapabilityFlags', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('returns both flags from rbac helpers in parallel', async () => {
    canOperateProject.mockResolvedValue(true)
    canConfigureProject.mockResolvedValue(false)

    const { getProjectCapabilityFlags } = await import('@/lib/auth/projectCapabilities')
    const flags = await getProjectCapabilityFlags('user-1', 'proj-1')

    expect(flags).toEqual({ canOperate: true, canConfigure: false })
    expect(canOperateProject).toHaveBeenCalledWith('user-1', 'proj-1')
    expect(canConfigureProject).toHaveBeenCalledWith('user-1', 'proj-1')
  })
})
