export type TranscriptParseResult = {
  text: string
  format: 'vtt' | 'txt' | 'json'
}

const normalizeLine = (s: string) => s.replace(/\r/g, '').trim()

const isVttTimestampLine = (line: string) =>
  /^\d{2}:\d{2}:\d{2}\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}/.test(line)

/**
 * Parses .vtt roughly into plain text (timestamps/headers stripped).
 */
export const parseVttToText = (raw: string) => {
  const lines = raw
    .split('\n')
    .map(normalizeLine)
    .filter((l) => l.length > 0)
    .filter((l) => l !== 'WEBVTT')
    .filter((l) => !isVttTimestampLine(l))
    .filter((l) => !/^[a-z-]+:\s*/i.test(l))

  const text = lines.join('\n').trim()
  return text
}

