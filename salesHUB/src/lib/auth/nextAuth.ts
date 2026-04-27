import type { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { prisma } from '@/lib/db/prisma'
import { isEmailAllowed } from '@/lib/auth/allowedEmail'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { ensureGmRole } from '@/lib/auth/rbac'
import { isGmEmail } from '@/lib/auth/gmEmail'

const must = (value: string | undefined, name: string) => {
  if (!value || value.trim().length === 0) {
    throw new Error(`${name} is required — add it to .env.local (see .env.example)`)
  }
  return value
}

const splitScopes = (raw: string) =>
  raw
    .split(/[,\s]+/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)

const googleScopes = () => {
  const fromEnv = process.env.GOOGLE_OAUTH_SCOPES?.trim()
  if (fromEnv) return splitScopes(fromEnv).join(' ')
  return 'openid email profile'
}

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  session: { strategy: 'database' },
  pages: {
    error: '/auth/error'
  },
  providers: [
    GoogleProvider({
      clientId: must(process.env.GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_ID'),
      clientSecret: must(process.env.GOOGLE_CLIENT_SECRET, 'GOOGLE_CLIENT_SECRET'),
      authorization: {
        params: {
          scope: googleScopes()
        }
      }
    })
  ],
  callbacks: {
    redirect: async ({ baseUrl }) => `${baseUrl}/auth/after`,
    session: async ({ session, user }) => {
      if (session.user) session.user.id = user.id
      return session
    },
    signIn: async ({ user }) => {
      const email = user.email?.trim().toLowerCase() ?? ''
      if (email.length === 0) return false

      const gm = isGmEmail(email)
      const allowed = gm ? true : await isEmailAllowed(email)
      if (!allowed) return false

      return true
    }
  },
  events: {
    signIn: async ({ user }) => {
      const email = user.email?.trim().toLowerCase() ?? ''
      if (!isGmEmail(email)) return

      const company = await getOrCreateDefaultCompany()
      const resolvedUserId =
        user.id ??
        (await prisma.user
          .findUnique({
            where: { email },
            select: { id: true }
          })
          .then((u) => u?.id ?? null))

      if (!resolvedUserId) return

      await ensureGmRole(resolvedUserId, company.id)
    }
  }
}
