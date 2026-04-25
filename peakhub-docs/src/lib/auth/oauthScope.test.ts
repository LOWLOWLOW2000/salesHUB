import { describe, expect, it } from 'vitest'
import { hasAllScopes, parseOAuthScope } from '@/lib/auth/oauthScope'

describe('oauthScope', () => {
  it('parseOAuthScope splits by spaces and commas', () => {
    expect(parseOAuthScope('openid email,profile')).toEqual(['openid', 'email', 'profile'])
  })

  it('hasAllScopes returns true when all required exist', () => {
    expect(hasAllScopes(['a', 'b', 'c'], ['a', 'c'])).toBe(true)
  })

  it('hasAllScopes returns false when a required scope is missing', () => {
    expect(hasAllScopes(['a', 'b'], ['a', 'c'])).toBe(false)
  })
})

