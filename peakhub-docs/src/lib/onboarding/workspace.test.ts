import { describe, expect, it, vi } from 'vitest'

vi.mock('@/lib/db/prisma', () => ({
  prisma: {
    workspace: {
      upsert: vi.fn(),
      create: vi.fn()
    },
    workspaceMember: {
      upsert: vi.fn()
    },
    user: {
      update: vi.fn(),
      findUnique: vi.fn()
    }
  }
}))

import { prisma } from '@/lib/db/prisma'
import {
  completeOnboarding,
  createClientWorkspace,
  getOrCreateIs01Workspace,
  getUserWorkspaceState,
  upsertWorkspaceMember
} from '@/lib/onboarding/workspace'

describe('workspace onboarding', () => {
  it('getOrCreateIs01Workspace upserts auto_squad IS01', async () => {
    ;(prisma.workspace.upsert as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'w1',
      type: 'auto_squad',
      name: 'IS01'
    })

    const w = await getOrCreateIs01Workspace()

    expect(prisma.workspace.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { type_name: { type: 'auto_squad', name: 'IS01' } }
      })
    )
    expect(w.id).toBe('w1')
  })

  it('createClientWorkspace creates client workspace', async () => {
    ;(prisma.workspace.create as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: 'w2',
      type: 'client',
      name: 'Acme'
    })

    const w = await createClientWorkspace('Acme')

    expect(prisma.workspace.create).toHaveBeenCalledWith(
      expect.objectContaining({ data: { type: 'client', name: 'Acme' } })
    )
    expect(w.type).toBe('client')
  })

  it('upsertWorkspaceMember upserts role', async () => {
    ;(prisma.workspaceMember.upsert as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'm1' })

    await upsertWorkspaceMember('w1', 'u1', 'owner')

    expect(prisma.workspaceMember.upsert).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { workspaceId_userId: { workspaceId: 'w1', userId: 'u1' } }
      })
    )
  })

  it('completeOnboarding sets completed timestamp and primary workspace', async () => {
    ;(prisma.user.update as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({ id: 'u1' })

    await completeOnboarding('u1', 'w1')

    expect(prisma.user.update).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { id: 'u1' },
        data: expect.objectContaining({ primaryWorkspaceId: 'w1' })
      })
    )
  })

  it('getUserWorkspaceState returns default state', async () => {
    ;(prisma.user.findUnique as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(null)

    const state = await getUserWorkspaceState('u1')

    expect(state.onboardingCompleted).toBe(false)
    expect(state.primaryWorkspaceId).toBe(null)
    expect(state.memberships).toEqual([])
  })
})

