/**
 * Aggregates CallLog rows into a compact summary line for AI prompts.
 */
export const formatCallLogSummary = (logs: { result: string }[]) => {
  if (logs.length === 0) return ''

  const counts = logs.reduce<Record<string, number>>((acc, log) => {
    acc[log.result] = (acc[log.result] ?? 0) + 1
    return acc
  }, {})

  const breakdown = Object.entries(counts)
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ja'))
    .map(([k, v]) => `${k}:${v}`)
    .join(', ')

  return `CallLog:${logs.length}件 / ${breakdown}`
}
