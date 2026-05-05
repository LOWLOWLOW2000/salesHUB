/**
 * Returns true when email matches GM_EMAIL (trim + lower).
 */
export const isGmEmail = (email: string) => {
  const expected = process.env.GM_EMAIL?.trim().toLowerCase() ?? ''
  if (expected.length === 0) return false
  return email.trim().toLowerCase() === expected
}
