import { prisma } from '@/lib/db/prisma'
import { verifyPassword } from '@/lib/auth/password'

export type CredentialUserForSession = {
  id: string
  email: string
  name: string | null
  image: string | null
}

/**
 * Validates email/password against a user row with `passwordHash` set.
 * Returns null when user missing, no hash, or password wrong.
 */
export const authenticateWithCredentials = async (
  normalizedEmail: string,
  password: string
): Promise<CredentialUserForSession | null> => {
  if (normalizedEmail.length === 0 || password.length === 0) return null

  const user = await prisma.user.findUnique({
    where: { email: normalizedEmail },
    select: {
      id: true,
      email: true,
      name: true,
      image: true,
      passwordHash: true
    }
  })

  if (!user?.passwordHash) return null
  const ok = await verifyPassword(password, user.passwordHash)
  if (!ok) return null

  return {
    id: user.id,
    email: user.email ?? normalizedEmail,
    name: user.name,
    image: user.image
  }
}
