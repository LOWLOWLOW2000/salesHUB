import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { basicAuth, isBasicAuthConfigured, isValidBasicAuthHeader } from '@/lib/auth/basic'

const shouldSkipAuth = (pathname: string) =>
  pathname.startsWith('/_next') ||
  pathname.startsWith('/favicon') ||
  pathname.startsWith('/robots.txt') ||
  pathname.startsWith('/sitemap.xml') ||
  pathname.startsWith('/api/auth') ||
  pathname.startsWith('/api/health') ||
  pathname.startsWith('/api/zoom') ||
  pathname.startsWith('/admin')

export const proxy = (request: NextRequest) => {
  if (!isBasicAuthConfigured()) return NextResponse.next()

  const { pathname } = request.nextUrl
  if (shouldSkipAuth(pathname)) return NextResponse.next()

  const authorization = request.headers.get('authorization')
  if (isValidBasicAuthHeader(authorization)) return NextResponse.next()

  return new NextResponse('Authentication required', {
    status: 401,
    headers: {
      'WWW-Authenticate': `Basic realm="${basicAuth.realm}", charset="UTF-8"`
    }
  })
}

export const config = {
  matcher: ['/((?!api/health).*)']
}
