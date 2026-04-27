import { describe, expect, test } from 'vitest'
import { buildFileSets, deriveFileSetKey, inferSourceRecordingRef } from './recordingFiles'

describe('recordingFiles', () => {
  test('deriveFileSetKey strips transcript suffix', () => {
    expect(deriveFileSetKey('/x/2026-04-27_foo_transcript.vtt')).toBe('2026-04-27_foo')
  })

  test('inferSourceRecordingRef extracts uuid', () => {
    expect(inferSourceRecordingRef('call_recording_c7d40f6b-8869-4b16-9ca7-547c7dbbbc9b_20260427081901')).toBe(
      'c7d40f6b-8869-4b16-9ca7-547c7dbbbc9b'
    )
  })

  test('buildFileSets pairs audio and transcript', () => {
    const files = [
      '/raw/2026-04-27/2026-04-27_Alice.mp3',
      '/raw/2026-04-27/2026-04-27_Alice_transcript.vtt',
      '/raw/2026-04-27/2026-04-27_Bob.mp3'
    ]
    const sets = buildFileSets(files)
    const alice = sets.find((s) => s.key.includes('Alice'))
    const bob = sets.find((s) => s.key.includes('Bob'))
    expect(alice?.transcriptPath).toMatch(/transcript\.vtt$/)
    expect(bob?.transcriptPath).toBeNull()
  })
})

