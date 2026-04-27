import { getServerSession } from 'next-auth/next'
import { authOptions } from '@/lib/auth/nextAuth'

export const getSession = async () => {
  const session = await getServerSession(authOptions)

  return session
}

