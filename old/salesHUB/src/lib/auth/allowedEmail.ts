import { prisma } from '@/lib/db/prisma'

const normalizeEmail = (email: string) => email.trim().toLowerCase()

/**
 * True when email is on AllowedEmail whitelist (normalized).
 */
export const isEmailAllowed = async (email: string) => {
  const normalized = normalizeEmail(email)
  if (normalized.length === 0) return false

  const row = await prisma.allowedEmail.findUnique({
    where: { email: normalized },
    select: { id: true }
  })

  return Boolean(row)
}
