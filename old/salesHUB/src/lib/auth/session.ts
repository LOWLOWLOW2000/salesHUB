import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth/nextAuth'

export const getSession = () => getServerSession(authOptions)
