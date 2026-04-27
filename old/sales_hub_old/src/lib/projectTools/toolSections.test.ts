import { describe, expect, it } from 'vitest'
import {
  getProjectToolSection,
  normalizeProjectToolId,
  projectToolSections
} from '@/lib/projectTools/toolSections'

describe('normalizeProjectToolId', () => {
  it('returns overview for empty or unknown', () => {
    expect(normalizeProjectToolId(null)).toBe('overview')
    expect(normalizeProjectToolId('')).toBe('overview')
    expect(normalizeProjectToolId('nope')).toBe('overview')
  })

  it('returns known ids', () => {
    expect(normalizeProjectToolId('pipeline')).toBe('pipeline')
    expect(normalizeProjectToolId('client-1st')).toBe('client-1st')
  })
})

describe('projectToolSections', () => {
  it('has unique ids', () => {
    const ids = projectToolSections.map((s) => s.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('getProjectToolSection returns blocks', () => {
    const s = getProjectToolSection('activity')
    expect(s?.blocks.length).toBeGreaterThan(0)
  })
})
