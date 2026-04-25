import type { NextAuthOptions } from 'next-auth'
import GoogleProvider from 'next-auth/providers/google'
import { PrismaAdapter } from '@auth/prisma-adapter'
import { prisma } from '@/lib/db/prisma'
import { isEmailAllowed } from '@/lib/auth/allowedEmail'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { ensureManagerRole } from '@/lib/auth/rbac'
import { isManagerEmail } from '@/lib/auth/managerEmail'

const must = (value: string | undefined, name: string) => {
  if (!value || value.trim().length === 0) throw new Error(`${name} is required`)
  return value
}

export const authOptions: NextAuthOptions = {
  adapter: PrismaAdapter(prisma),
  session: { strategy: 'database' },
  providers: [
    GoogleProvider({
      clientId: must(process.env.GOOGLE_CLIENT_ID, 'GOOGLE_CLIENT_ID'),
      clientSecret: must(process.env.GOOGLE_CLIENT_SECRET, 'GOOGLE_CLIENT_SECRET')
    })
  ],
  callbacks: {
    signIn: async ({ user }) => {
      const email = user.email?.trim().toLowerCase() ?? ''
      if (email.length === 0) return false

      const isManager = isManagerEmail(email)
      const allowed = isManager ? true : await isEmailAllowed(email)
      if (!allowed) return false

      if (isManager) {
        const company = await getOrCreateDefaultCompany()
        await ensureManagerRole(user.id, company.id)
      }

      return true
    }
  }
}

