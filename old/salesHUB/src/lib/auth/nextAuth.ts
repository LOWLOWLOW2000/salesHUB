import type { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import CredentialsProvider from 'next-auth/providers/credentials'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { prisma } from '@/lib/db/prisma'
import { isEmailAllowed } from '@/lib/auth/allowedEmail'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { ensureGmRole } from '@/lib/auth/rbac'
import { isGmEmail } from '@/lib/auth/gmEmail'
import { authenticateWithCredentials } from '@/lib/auth/credentialsAuth'
import { isCredentialsAuthEnabled, isGoogleOAuthConfigured } from '@/lib/auth/authProvidersEnv'

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

const googleClientId = process.env.GOOGLE_CLIENT_ID?.trim()
const googleClientSecret = process.env.GOOGLE_CLIENT_SECRET?.trim()

const providers = [
  ...(isGoogleOAuthConfigured()
    ? [
        GoogleProvider({
          clientId: googleClientId!,
          clientSecret: googleClientSecret!,
          authorization: {
            params: {
              scope: googleScopes()
            }
          }
        })
      ]
    : []),
  ...(isCredentialsAuthEnabled()
    ? [
        CredentialsProvider({
          id: 'credentials',
          name: 'Email and password',
          credentials: {
            email: { label: 'Email', type: 'email' },
            password: { label: 'Password', type: 'password' }
          },
          async authorize(credentials) {
            const email = credentials?.email?.trim().toLowerCase() ?? ''
            const password = String(credentials?.password ?? '')
            const user = await authenticateWithCredentials(email, password)
            if (!user) return null
            return {
              id: user.id,
              email: user.email,
              name: user.name,
              image: user.image
            }
          }
        })
      ]
    : [])
]

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  session: { strategy: isCredentialsAuthEnabled() ? 'jwt' : 'database' },
  pages: {
    signIn: '/auth/signin',
    error: '/auth/error'
  },
  providers,
  callbacks: {
    redirect: async ({ baseUrl }) => `${baseUrl}/auth/after`,
    session: async ({ session, user, token }) => {
      const resolvedUserId = user?.id ?? (typeof token?.sub === 'string' ? token.sub : null)
      if (session.user && resolvedUserId) session.user.id = resolvedUserId
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
