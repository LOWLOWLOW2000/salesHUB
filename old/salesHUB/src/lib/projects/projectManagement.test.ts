import { describe, expect, it } from 'vitest'
import {
  sortMembersForManagement,
  toRoleCategory,
  toSavedProjectRole,
  type MemberRow
} from '@/lib/projects/projectManagement'

describe('projectManagement', () => {
  it('toRoleCategory picks highest tier', () => {
    expect(toRoleCategory(['is'])).toBe('member')
    expect(toRoleCategory(['as'])).toBe('member')
    expect(toRoleCategory(['leader', 'is'])).toBe('leader')
    expect(toRoleCategory(['director', 'leader', 'is'])).toBe('director')
  })

  it('toSavedProjectRole maps member to is', () => {
    expect(toSavedProjectRole('member')).toBe('is')
    expect(toSavedProjectRole('leader')).toBe('leader')
    expect(toSavedProjectRole('director')).toBe('director')
  })

  it('sortMembersForManagement sorts by tier then name', () => {
    const rows: MemberRow[] = [
      { userId: 'u3', name: 'いとう', email: 'ito@example.com', roles: ['is'] },
      { userId: 'u2', name: 'あべ', email: 'abe@example.com', roles: ['leader'] },
      { userId: 'u1', name: 'かとう', email: 'kato@example.com', roles: ['director'] }
    ]

    const sorted = sortMembersForManagement(rows).map((r) => r.userId)
    expect(sorted).toEqual(['u1', 'u2', 'u3'])
  })
})

