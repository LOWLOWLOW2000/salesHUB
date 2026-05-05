import type { AppRole } from '@prisma/client'

export type RoleCategory = 'director' | 'leader' | 'member'

export type MemberRow = {
  userId: string
  name: string | null
  email: string | null
  roles: AppRole[]
}

const categoryPriority: RoleCategory[] = ['director', 'leader', 'member']

/**
 * Map raw project roles into a single exclusive category for UI.
 * - `director` wins
 * - else `leader`
 * - else `member` (includes `as`/`is`/`fs`/`cs`)
 */
export const toRoleCategory = (roles: AppRole[]): RoleCategory => {
  const set = new Set(roles)
  if (set.has('director')) return 'director'
  if (set.has('leader')) return 'leader'
  return 'member'
}

export const toDisplayName = (name: string | null, email: string | null) => {
  const n = (name ?? '').trim()
  if (n.length > 0) return n
  return (email ?? '').trim()
}

/**
 * Sort: tier high → low, then by display name (ja).
 */
export const sortMembersForManagement = (rows: MemberRow[]) =>
  [...rows].sort((a, b) => {
    const ca = toRoleCategory(a.roles)
    const cb = toRoleCategory(b.roles)
    const pa = categoryPriority.indexOf(ca)
    const pb = categoryPriority.indexOf(cb)
    if (pa !== pb) return pa - pb

    const da = toDisplayName(a.name, a.email)
    const db = toDisplayName(b.name, b.email)
    return da.localeCompare(db, 'ja')
  })

/**
 * Exclusive save mapping. For now, Member is always `is`.
 */
export const toSavedProjectRole = (category: RoleCategory): AppRole =>
  category === 'director' ? 'director' : category === 'leader' ? 'leader' : 'is'

