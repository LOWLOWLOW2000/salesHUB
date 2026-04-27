import { NextResponse } from 'next/server'
import { z } from 'zod'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import { sendMaterialEmail } from '@/lib/materials/sendMaterialEmail'

const bodySchema = z.object({
  to: z.string().email(),
  accountId: z.string().min(1),
  contactId: z.string().optional(),
  assetIds: z.array(z.string()).min(1),
  subject: z.string().min(1).max(200).optional()
})

/**
 * Sends a simple summary email listing selected material URLs (GM only).
 */
export const POST = async (req: Request) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) return NextResponse.json({ error: 'unauthorized' }, { status: 401 })

  const company = await getOrCreateDefaultCompany()
  if (!(await hasCompanyRole(userId, company.id, 'gm'))) {
    return NextResponse.json({ error: 'forbidden' }, { status: 403 })
  }

  const json = await req.json().catch(() => null)
  const parsed = bodySchema.safeParse(json)
  if (!parsed.success) return NextResponse.json({ error: 'bad_request' }, { status: 400 })

  const account = await prisma.salesAccount.findFirst({
    where: { id: parsed.data.accountId, companyId: company.id },
    select: { id: true }
  })
  if (!account) return NextResponse.json({ error: 'account_not_found' }, { status: 404 })

  const assets = await prisma.materialAsset.findMany({
    where: { id: { in: parsed.data.assetIds }, companyId: company.id },
    select: { name: true, fileUrl: true }
  })

  const lines = assets.map((a) => `- ${a.name}: ${a.fileUrl}`).join('\n')
  const subject = parsed.data.subject ?? 'salesHUB materials'
  const text = `Materials:\n${lines}`

  const send = await sendMaterialEmail({
    to: parsed.data.to,
    subject,
    text
  })

  if (!send.ok) {
    return NextResponse.json({ error: send.error }, { status: 400 })
  }

  await prisma.materialSendLog.create({
    data: {
      accountId: parsed.data.accountId,
      contactId: parsed.data.contactId,
      userId,
      assetIds: parsed.data.assetIds,
      mode: 'email',
      status: 'ok'
    }
  })

  return NextResponse.json({ ok: true })
}
