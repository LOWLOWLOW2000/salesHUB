/**
 * Basic認証（ローカル運用向け）
 *
 * - 認証情報は環境変数で管理する
 * - 将来SSOに置き換える前提で、ロジックをここに集約する
 */
export const basicAuth = {
  realm: process.env.BASIC_AUTH_REALM?.trim() || 'Sales Consulting Hub',
  envUserKey: 'BASIC_AUTH_USER',
  envPassKey: 'BASIC_AUTH_PASS'
} as const

export const getBasicAuthCredentials = () => ({
  user: process.env[basicAuth.envUserKey] ?? '',
  pass: process.env[basicAuth.envPassKey] ?? ''
})

export const isBasicAuthConfigured = () => {
  const { user, pass } = getBasicAuthCredentials()
  return user.length > 0 && pass.length > 0
}

export const toBasicAuthHeaderValue = (user: string, pass: string) => {
  const token = Buffer.from(`${user}:${pass}`).toString('base64')
  return `Basic ${token}`
}

export const isValidBasicAuthHeader = (authorization: string | null) => {
  if (!authorization?.startsWith('Basic ')) return false

  const { user, pass } = getBasicAuthCredentials()
  if (user.length === 0 || pass.length === 0) return false

  const expected = toBasicAuthHeaderValue(user, pass)
  return authorization === expected
}

