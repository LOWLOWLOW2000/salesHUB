import { NextResponse } from 'next/server'
import { z } from 'zod'
import { getSession } from '@/lib/auth/session'
import { canOperateProject } from '@/lib/auth/rbac'
import { createZoomDialSession } from '@/lib/zoom/zoomServer'

const bodySchema = z.object({
  projectId: z.string().min(1)
})

export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const json = await req.json().catch(() => null)
  const parsed = bodySchema.safeParse(json)
  if (!parsed.success) return NextResponse.json({ error: 'bad_request' }, { status: 400 })

  if (!(await canOperateProject(userId, parsed.data.projectId))) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 })
  }

  const dial = await createZoomDialSession()
  return NextResponse.json(dial)
}
