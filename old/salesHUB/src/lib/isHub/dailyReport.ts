import { z } from 'zod'

const nonNegativeInt = z.coerce.number().int().min(0).max(100000)

export const dailyReportFormSchema = z.object({
  projectId: z.string().min(1),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  callCount: nonNegativeInt,
  connectCount: nonNegativeInt,
  receptionNgCount: nonNegativeInt,
  keymanNgCount: nonNegativeInt,
  materialSentCount: nonNegativeInt,
  appointmentCount: nonNegativeInt,
  callMinutes: nonNegativeInt,
  totalMinutes: nonNegativeInt,
  notes: z.string().max(4000).default(''),
  callSlots: z.string().max(4000).default(''),
  receptionNgReasons: z.string().max(4000).default(''),
  keymanNgReasons: z.string().max(4000).default(''),
  appointmentReasonTags: z.string().max(4000).default('')
})

export type DailyReportInput = z.infer<typeof dailyReportFormSchema>

export type KpiMetrics = {
  callCount: number
  connectCount: number
  receptionNgCount: number
  keymanNgCount: number
  materialSentCount: number
  appointmentCount: number
  callMinutes: number
  totalMinutes: number
  keymanConnectRate: number
  receptionPassRate: number
  nextActionRate: number
  appointmentRate: number
}

export const emptyKpiMetrics = (): KpiMetrics => ({
  callCount: 0,
  connectCount: 0,
  receptionNgCount: 0,
  keymanNgCount: 0,
  materialSentCount: 0,
  appointmentCount: 0,
  callMinutes: 0,
  totalMinutes: 0,
  keymanConnectRate: 0,
  receptionPassRate: 0,
  nextActionRate: 0,
  appointmentRate: 0
})

export const parseDateInput = (date: string) => new Date(`${date}T00:00:00.000Z`)

export const toDateInput = (date: Date) => date.toISOString().slice(0, 10)

export const todayDateInput = () => toDateInput(new Date())

export const formatRate = (rate: number) => `${(rate * 100).toFixed(1)}%`

const safeRate = (numerator: number, denominator: number) =>
  denominator > 0 ? numerator / denominator : 0

export const buildKpiMetrics = (
  reports: Array<{
    callCount: number
    connectCount: number
    receptionNgCount: number
    keymanNgCount: number
    materialSentCount: number
    appointmentCount: number
    callMinutes: number
    totalMinutes: number
  }>
): KpiMetrics => {
  const totals = reports.reduce(
    (acc, report) => ({
      callCount: acc.callCount + report.callCount,
      connectCount: acc.connectCount + report.connectCount,
      receptionNgCount: acc.receptionNgCount + report.receptionNgCount,
      keymanNgCount: acc.keymanNgCount + report.keymanNgCount,
      materialSentCount: acc.materialSentCount + report.materialSentCount,
      appointmentCount: acc.appointmentCount + report.appointmentCount,
      callMinutes: acc.callMinutes + report.callMinutes,
      totalMinutes: acc.totalMinutes + report.totalMinutes
    }),
    {
      callCount: 0,
      connectCount: 0,
      receptionNgCount: 0,
      keymanNgCount: 0,
      materialSentCount: 0,
      appointmentCount: 0,
      callMinutes: 0,
      totalMinutes: 0
    }
  )

  return {
    ...totals,
    keymanConnectRate: safeRate(totals.connectCount, totals.callCount),
    receptionPassRate: safeRate(totals.callCount - totals.receptionNgCount, totals.callCount),
    nextActionRate: safeRate(totals.materialSentCount + totals.appointmentCount, totals.connectCount),
    appointmentRate: safeRate(totals.appointmentCount, totals.connectCount)
  }
}

export const splitLines = (raw: string) =>
  raw
    .split(/\r?\n|,/g)
    .map((line) => line.trim())
    .filter((line) => line.length > 0)

export const countTokens = (values: string[]) =>
  [...values.reduce((map, value) => map.set(value, (map.get(value) ?? 0) + 1), new Map<string, number>())]
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label, 'ja'))

export const summarizeBottleneck = (metrics: KpiMetrics) => {
  if (metrics.callCount === 0) return 'まだ架電データがありません。まずは日報入力で母数を作ります。'
  if (metrics.keymanConnectRate < 0.15) return 'キーマン接続率が低めです。時間帯・番号品質・受付呼出し方を優先して見直します。'
  if (metrics.nextActionRate < 0.3) return '次アクション率が低めです。資料送付・日時切り・追客合意の型を見直します。'
  if (metrics.appointmentRate < 0.15) return 'アポ率が低めです。インパクトアプローチと切返し後クロージングを重点改善します。'
  return '主要KPIは一定水準です。勝ち要因タグを横展開し、リスト別の再現性を高めます。'
}
