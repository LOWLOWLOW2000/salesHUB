import { NextResponse } from 'next/server'
import { z } from 'zod'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import {
  completeOnboarding,
  createClientWorkspace,
  getOrCreateIs01Workspace,
  upsertWorkspaceMember
} from '@/lib/onboarding/workspace'

const trackSchema = z.discriminatedUnion('action', [
  z.object({
    action: z.literal('createClientWorkspace'),
    name: z.string().trim().min(1),
    role: z.enum(['owner', 'director', 'member'])
  }),
  z.object({
    action: z.literal('joinAutoSquad'),
    role: z.enum(['is', 'fs', 'manager'])
  }),
  z.object({
    action: z.literal('complete'),
    workspaceId: z.string().min(1),
    displayName: z.string().trim().min(1)
  })
])

export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const json = await req.json().catch(() => null)
  const parsed = trackSchema.safeParse(json)
  if (!parsed.success) return NextResponse.json({ error: 'bad_request' }, { status: 400 })

  if (parsed.data.action === 'createClientWorkspace') {
    const workspace = await createClientWorkspace(parsed.data.name)
    await upsertWorkspaceMember(workspace.id, userId, parsed.data.role)

    return NextResponse.json({ workspaceId: workspace.id })
  }

  if (parsed.data.action === 'joinAutoSquad') {
    const workspace = await getOrCreateIs01Workspace()
    await upsertWorkspaceMember(workspace.id, userId, parsed.data.role)

    return NextResponse.json({ workspaceId: workspace.id })
  }

  const updatedName = parsed.data.displayName.trim()
  await prisma.user.update({
    where: { id: userId },
    data: { name: updatedName }
  })

  await completeOnboarding(userId, parsed.data.workspaceId)

  return NextResponse.json({ ok: true })
}

