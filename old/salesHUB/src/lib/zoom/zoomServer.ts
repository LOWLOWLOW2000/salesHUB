/**
 * Zoom Server-to-Server OAuth + instant meeting (minimal).
 */

const getZoomAccessToken = async (): Promise<string | null> => {
  const accountId = process.env.ZOOM_ACCOUNT_ID?.trim()
  const clientId = process.env.ZOOM_CLIENT_ID?.trim()
  const secret = process.env.ZOOM_CLIENT_SECRET?.trim()
  if (!accountId || !clientId || !secret) return null

  const basic = Buffer.from(`${clientId}:${secret}`).toString('base64')
  const res = await fetch(
    `https://zoom.us/oauth/token?grant_type=account_credentials&account_id=${encodeURIComponent(accountId)}`,
    {
      method: 'POST',
      headers: { authorization: `Basic ${basic}` }
    }
  )

  if (!res.ok) return null
  const data = (await res.json()) as { access_token?: string }
  return typeof data.access_token === 'string' ? data.access_token : null
}

export type ZoomDialResult = {
  mode: 'live' | 'mock'
  joinUrl: string
  meetingId: string | null
}

/**
 * Creates a Zoom meeting when credentials are configured; otherwise returns mock URL.
 */
export const createZoomDialSession = async (): Promise<ZoomDialResult> => {
  const token = await getZoomAccessToken()
  if (!token) {
    return { mode: 'mock', joinUrl: 'https://zoom.us/download', meetingId: null }
  }

  const res = await fetch('https://api.zoom.us/v2/users/me/meetings', {
    method: 'POST',
    headers: {
      authorization: `Bearer ${token}`,
      'content-type': 'application/json'
    },
    body: JSON.stringify({
      topic: 'salesHUB dial',
      type: 1,
      settings: { join_before_host: true }
    })
  })

  if (!res.ok) {
    return { mode: 'mock', joinUrl: 'https://zoom.us/download', meetingId: null }
  }

  const data = (await res.json()) as { join_url?: string; id?: number | string }
  const joinUrl = typeof data.join_url === 'string' ? data.join_url : 'https://zoom.us/download'
  const meetingId = data.id != null ? String(data.id) : null

  return { mode: 'live', joinUrl, meetingId }
}
