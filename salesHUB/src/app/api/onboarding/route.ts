import { NextResponse } from 'next/server'
import { z } from 'zod'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import type { AppRole } from '@prisma/client'

const bodySchema = z.object({
  action: z.literal('complete'),
  displayName: z.string().trim().min(1),
  role: z.enum(['director', 'as', 'is', 'fs', 'cs'])
})

export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const json = await req.json().catch(() => null)
  const parsed = bodySchema.safeParse(json)
  if (!parsed.success) return NextResponse.json({ error: 'bad_request' }, { status: 400 })

  const company = await getOrCreateDefaultCompany()
  const isGmUser = await hasCompanyRole(userId, company.id, 'gm')

  await prisma.user.update({
    where: { id: userId },
    data: {
      name: parsed.data.displayName.trim(),
      onboardingCompletedAt: new Date()
    }
  })

  if (!isGmUser) {
    const role = parsed.data.role as AppRole
    await prisma.companyMember.upsert({
      where: {
        companyId_userId_role: {
          companyId: company.id,
          userId,
          role
        }
      },
      update: {},
      create: {
        companyId: company.id,
        userId,
        role
      }
    })
  }

  return NextResponse.json({ ok: true })
}
