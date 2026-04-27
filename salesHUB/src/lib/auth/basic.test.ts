import { describe, expect, it, vi } from 'vitest'
import { isValidBasicAuthHeader, toBasicAuthHeaderValue } from '@/lib/auth/basic'

describe('basic auth', () => {
  it('creates basic auth header', () => {
    expect(toBasicAuthHeaderValue('a', 'b')).toBe('Basic YTpi')
  })

  it('validates header using env credentials', () => {
    vi.stubEnv('BASIC_AUTH_USER', 'user')
    vi.stubEnv('BASIC_AUTH_PASS', 'pass')

    const header = toBasicAuthHeaderValue('user', 'pass')
    expect(isValidBasicAuthHeader(header)).toBe(true)
    expect(isValidBasicAuthHeader(toBasicAuthHeaderValue('user', 'wrong'))).toBe(false)
  })
})

