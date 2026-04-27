export const parseOAuthScope = (raw: string | null | undefined) =>
  (raw ?? '')
    .split(/[,\s]+/g)
    .map((s) => s.trim())
    .filter((s) => s.length > 0)

export const hasAllScopes = (granted: string[], required: string[]) => {
  const grantedSet = new Set(granted)
  return required.every((s) => grantedSet.has(s))
}

export const requiredGoogleScopes = () => {
  const raw = process.env.GOOGLE_REQUIRED_SCOPES?.trim()
  if (!raw) return []
  return parseOAuthScope(raw)
}
