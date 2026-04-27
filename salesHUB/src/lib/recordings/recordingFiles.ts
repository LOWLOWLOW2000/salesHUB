import path from 'path'

export type RecordingFileSet = {
  /** Stable key for grouping audio+transcript */
  key: string
  /** Absolute path to audio file */
  audioPath: string
  /** Absolute path to transcript file when present */
  transcriptPath: string | null
  /** Best-effort recordedAt (derived from filename/folder) */
  recordedAt: Date
  /** Optional extracted source id (uuid etc) */
  sourceRecordingRef: string
  callerLabel: string
}

const parseYmd = (ymd: string) => {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(ymd)) return null
  const d = new Date(`${ymd}T00:00:00+09:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

const parseYmdHmsCompact = (s: string) => {
  if (!/^\d{14}$/.test(s)) return null
  const yyyy = s.slice(0, 4)
  const mm = s.slice(4, 6)
  const dd = s.slice(6, 8)
  const hh = s.slice(8, 10)
  const mi = s.slice(10, 12)
  const ss = s.slice(12, 14)
  const d = new Date(`${yyyy}-${mm}-${dd}T${hh}:${mi}:${ss}+09:00`)
  return Number.isNaN(d.getTime()) ? null : d
}

const normalizeKey = (s: string) => s.trim().replace(/\s+/g, ' ')

const stripExt = (filename: string) => filename.replace(/\.[^.]+$/, '')

const isAudioExt = (ext: string) => ['.mp3', '.m4a', '.wav'].includes(ext.toLowerCase())

const isTranscriptExt = (ext: string) => ['.vtt', '.txt', '.json'].includes(ext.toLowerCase())

export const deriveFileSetKey = (filePath: string) => {
  const base = path.basename(filePath)
  const noExt = stripExt(base)
  return normalizeKey(noExt.replace(/_transcript$/i, ''))
}

export const inferSourceRecordingRef = (fileSetKey: string) => {
  const m = fileSetKey.match(/call_recording_([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/i)
  return m?.[1]?.toLowerCase() ?? fileSetKey
}

export const inferRecordedAt = (filePath: string) => {
  const dir = path.basename(path.dirname(filePath))
  const fromDir = parseYmd(dir)
  const base = stripExt(path.basename(filePath))

  const compact = base.match(/_(\d{14})$/)?.[1] ?? null
  const fromCompact = compact ? parseYmdHmsCompact(compact) : null

  return fromCompact ?? fromDir ?? new Date()
}

export const inferCallerLabel = (filePath: string) => {
  const base = stripExt(path.basename(filePath))
  const m1 = base.match(/^\d{4}-\d{2}-\d{2}_(.+)$/)?.[1]
  if (m1) return m1.replace(/_transcript$/i, '')

  const m2 = base.match(/^call_recording_[0-9a-f-]{36}_(\d{14})$/i)
  if (m2) return ''

  return ''
}

export const buildFileSets = (filePaths: string[]): RecordingFileSet[] => {
  const audio = filePaths
    .filter((p) => isAudioExt(path.extname(p)))
    .map((audioPath) => {
      const key = deriveFileSetKey(audioPath)
      const transcriptPath =
        filePaths.find((p) => deriveFileSetKey(p) === key && isTranscriptExt(path.extname(p))) ?? null

      const recordedAt = inferRecordedAt(audioPath)
      const callerLabel = inferCallerLabel(audioPath)
      const sourceRecordingRef = inferSourceRecordingRef(key)

      return { key, audioPath, transcriptPath, recordedAt, sourceRecordingRef, callerLabel }
    })

  const uniqByRef = new Map(audio.map((a) => [a.sourceRecordingRef, a] as const))
  return [...uniqByRef.values()]
}

