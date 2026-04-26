import { NextResponse } from 'next/server'
import { getSession } from '@/lib/auth/session'

export const GET = async () => {
  const session = await getSession()
  return NextResponse.json({ session })
}

