import crypto from 'crypto'
import { NextResponse } from 'next/server'

/**
 * Zoom endpoint URL validation (challenge) + no-op event sink.
 */
export const POST = async (req: Request) => {
  const secret = process.env.ZOOM_WEBHOOK_SECRET_TOKEN?.trim() ?? ''
  const body = await req.json().catch(() => null)

  if (!body || typeof body !== 'object') {
    return NextResponse.json({ received: true })
  }

  if (body.event === 'endpoint.url_validation' && secret.length > 0) {
    const plainToken = body.payload?.plainToken as string | undefined
    if (!plainToken) return NextResponse.json({ error: 'bad_request' }, { status: 400 })

    const encryptedToken = crypto.createHmac('sha256', secret).update(plainToken).digest('hex')
    return NextResponse.json({
      plainToken,
      encryptedToken
    })
  }

  return NextResponse.json({ received: true })
}
