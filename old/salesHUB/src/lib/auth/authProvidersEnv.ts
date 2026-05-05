/** Env flags shared by NextAuth and the sign-in page. */

export const isCredentialsAuthEnabled = () => {
  const v = process.env.ENABLE_CREDENTIALS_AUTH?.trim().toLowerCase() ?? ''
  return v === 'true' || v === '1' || v === 'yes'
}

export const isGoogleOAuthConfigured = () => {
  const id = process.env.GOOGLE_CLIENT_ID?.trim()
  const secret = process.env.GOOGLE_CLIENT_SECRET?.trim()
  return Boolean(id && secret)
}
