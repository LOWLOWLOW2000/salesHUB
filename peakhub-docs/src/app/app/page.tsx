import Link from 'next/link'
import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth/session'
import { prisma } from '@/lib/db/prisma'

export default async function AppHome() {
  await getSession()
  redirect('/')
}

