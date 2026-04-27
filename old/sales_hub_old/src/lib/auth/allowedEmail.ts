import { prisma } from '@/lib/db/prisma'

/**
 * アプリ利用を許可するメールアドレスか（ホワイトリスト方式）
 */
export const isEmailAllowed = async (email: string) => {
  const normalized = email.trim().toLowerCase()
  if (normalized.length === 0) return false

  const found = await prisma.allowedEmail.findUnique({
    where: { email: normalized },
    select: { id: true }
  })

  return Boolean(found)
}

