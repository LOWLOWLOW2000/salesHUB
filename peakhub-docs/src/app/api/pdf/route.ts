import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'
import { chromium } from 'playwright'
import { getBasicAuthCredentials, isBasicAuthConfigured } from '@/lib/auth/basic'

const toTargetUrl = (origin: string, path: string) => {
  const normalized = path.startsWith('/') ? path : `/${path}`
  return `${origin}${normalized}`
}

const getRequestedPath = (request: NextRequest) => request.nextUrl.searchParams.get('path') ?? '/'

export const GET = async (request: NextRequest) => {
  const origin = request.nextUrl.origin
  const path = getRequestedPath(request)

  if (!path.startsWith('/')) {
    return NextResponse.json({ error: 'Invalid path' }, { status: 400 })
  }

  const browser = await chromium.launch()

  try {
    const context = await browser.newContext({
      ...(isBasicAuthConfigured()
        ? {
            httpCredentials: {
              username: getBasicAuthCredentials().user,
              password: getBasicAuthCredentials().pass
            }
          }
        : {})
    })

    const page = await context.newPage()

    await page.goto(toTargetUrl(origin, path), { waitUntil: 'networkidle' })
    const pdf = await page.pdf({
      format: 'A4',
      printBackground: true,
      margin: { top: '12mm', right: '12mm', bottom: '12mm', left: '12mm' }
    })

    await context.close()

    const body = Uint8Array.from(pdf).buffer

    return new NextResponse(body, {
      status: 200,
      headers: {
        'Content-Type': 'application/pdf',
        'Content-Disposition': `attachment; filename="peakhub-docs${path
          .replaceAll('/', '_')
          .replaceAll('\\\\', '_')}.pdf"`
      }
    })
  } finally {
    await browser.close()
  }
}

