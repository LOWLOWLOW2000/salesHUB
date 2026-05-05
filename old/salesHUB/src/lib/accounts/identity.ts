import crypto from 'crypto'

/**
 * Normalizes company name for stable keys (IS_01 compatible).
 */
export const normalizeCompanyName = (nameRaw: string): string =>
  nameRaw
    .replace(/\s+/g, ' ')
    .trim()

/**
 * Digits-only phone normalization.
 */
export const normalizePhone = (phoneRaw: string): string =>
  phoneRaw
    .replace(/[^\d]/g, '')
    .trim()

/**
 * External row id: cr_ + first 16 hex chars of SHA1(nameNorm|phoneNorm).
 */
export const createClientRowId = (companyNameNorm: string, phoneNorm: string): string => {
  const base = `${companyNameNorm}|${phoneNorm}`
  const digest = crypto.createHash('sha1').update(base, 'utf8').digest('hex')
  return `cr_${digest.slice(0, 16)}`
}

/**
 * Best-effort hostname from a website URL column.
 */
export const domainFromUrl = (raw: string): string => {
  try {
    const href = raw.startsWith('http://') || raw.startsWith('https://') ? raw : `https://${raw}`
    return new URL(href).hostname
  } catch {
    return ''
  }
}

