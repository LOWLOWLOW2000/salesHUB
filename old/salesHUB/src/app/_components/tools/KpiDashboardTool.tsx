import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { prisma } from '@/lib/db/prisma'
import { getSession } from '@/lib/auth/session'
import { canViewProject } from '@/lib/projects/accessibleProjects'
import {
  buildKpiMetrics,
  countTokens,
  formatRate,
  splitLines,
  summarizeBottleneck,
  toDateInput
} from '@/lib/isHub/dailyReport'
import { buildImprovementSuggestion } from '@/lib/isHub/aiSuggestion'
import { formatCallLogSummary } from '@/lib/isHub/callLogMetrics'

type Props = {
  projectId: string
}

const startOfDayUtc = (date: Date) =>
  new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()))

const addDays = (date: Date, days: number) => {
  const next = new Date(date)
  next.setUTCDate(next.getUTCDate() + days)
  return next
}

/** KPI の AI 提案保存: 閲覧できるユーザーなら誰でも（canViewProject と同ティア）。 */
const generateImprovementSuggestion = async (formData: FormData) => {
  'use server'

  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const projectId = String(formData.get('projectId') ?? '')
  if (!(await canViewProject(userId, projectId))) redirect('/')

  const periodEnd = startOfDayUtc(new Date())
  const periodStart = addDays(periodEnd, -27)
  const reports = await prisma.dailyReport.findMany({
    where: {
      projectId,
      date: { gte: periodStart, lte: periodEnd }
    }
  })
  const metrics = buildKpiMetrics(reports)
  const topReceptionNgReasons = countTokens(reports.flatMap((r) => splitLines(r.receptionNgReasons))).slice(0, 5)
  const topKeymanNgReasons = countTokens(reports.flatMap((r) => splitLines(r.keymanNgReasons))).slice(0, 5)
  const topAppointmentReasons = countTokens(reports.flatMap((r) => splitLines(r.appointmentReasonTags))).slice(0, 5)
  const callLogs = await prisma.callLog.findMany({
    where: {
      projectId,
      startedAt: { gte: periodStart, lt: addDays(periodEnd, 1) }
    },
    select: { result: true }
  })
  const callLogSummary = formatCallLogSummary(callLogs)
  const { promptSummary, suggestion } = await buildImprovementSuggestion({
    metrics,
    topReceptionNgReasons,
    topKeymanNgReasons,
    topAppointmentReasons,
    callLogSummary: callLogSummary.length > 0 ? callLogSummary : undefined
  })

  await prisma.aiSuggestion.create({
    data: {
      projectId,
      periodStart,
      periodEnd,
      promptSummary,
      suggestion
    }
  })

  revalidatePath(`/project/${projectId}`)
}

const MetricCard = ({ label, value, sub }: { label: string; value: string; sub: string }) => (
  <div className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
    <div className="text-xs font-medium text-zinc-500">{label}</div>
    <div className="mt-2 text-2xl font-semibold tracking-tight text-zinc-950">{value}</div>
    <div className="mt-1 text-xs text-zinc-600">{sub}</div>
  </div>
)

/**
 * 日報を週次・月次・担当別に集計し、改善の見る順を明示するダッシュボード。
 */
export const KpiDashboardTool = async ({ projectId }: Props) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const periodEnd = startOfDayUtc(new Date())
  const periodStart = addDays(periodEnd, -27)
  const monthStart = new Date(Date.UTC(periodEnd.getUTCFullYear(), periodEnd.getUTCMonth(), 1))
  const reports = await prisma.dailyReport.findMany({
    where: {
      projectId,
      date: { gte: periodStart, lte: periodEnd }
    },
    orderBy: { date: 'asc' },
    include: { user: { select: { name: true, email: true } } }
  })
  const monthReports = reports.filter((r) => r.date >= monthStart)
  const totalMetrics = buildKpiMetrics(reports)
  const monthMetrics = buildKpiMetrics(monthReports)
  const weeklyMetrics = Array.from({ length: 4 }, (_, index) => {
    const start = addDays(periodStart, index * 7)
    const end = addDays(start, 6)
    return {
      start,
      end,
      metrics: buildKpiMetrics(reports.filter((r) => r.date >= start && r.date <= end))
    }
  })

  const playerRows = [
    ...reports
      .reduce((map, report) => {
        const label = report.user.name ?? report.user.email ?? 'unknown'
        return map.set(label, [...(map.get(label) ?? []), report])
      }, new Map<string, typeof reports>())
      .entries()
  ].map(([label, rows]) => ({ label, metrics: buildKpiMetrics(rows) }))

  const topReceptionNgReasons = countTokens(reports.flatMap((r) => splitLines(r.receptionNgReasons))).slice(0, 5)
  const topKeymanNgReasons = countTokens(reports.flatMap((r) => splitLines(r.keymanNgReasons))).slice(0, 5)
  const topAppointmentReasons = countTokens(reports.flatMap((r) => splitLines(r.appointmentReasonTags))).slice(0, 5)
  const callSlotLines = reports.flatMap((r) => splitLines(r.callSlots)).slice(-12).reverse()
  const suggestions = await prisma.aiSuggestion.findMany({
    where: { projectId },
    orderBy: { createdAt: 'desc' },
    take: 3
  })

  const callLogs = await prisma.callLog.findMany({
    where: {
      projectId,
      startedAt: { gte: periodStart, lt: addDays(periodEnd, 1) }
    },
    select: {
      id: true,
      result: true,
      startedAt: true,
      user: { select: { name: true, email: true } }
    },
    orderBy: { startedAt: 'desc' },
    take: 200
  })
  const callLogSummaryLine = formatCallLogSummary(callLogs)

  return (
    <div className="space-y-7">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-zinc-950">KPIダッシュボード</h2>
          <p className="mt-1 text-sm text-zinc-600">
            直近4週の活動量・接続率・次アクション率・アポ率を、改善の見る順で確認します。
          </p>
        </div>
        <form action={generateImprovementSuggestion}>
          <input type="hidden" name="projectId" value={projectId} />
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            改善示唆を生成
          </button>
        </form>
      </header>

      <div className="grid gap-3 md:grid-cols-4">
        <MetricCard label="キーマン接続率" value={formatRate(totalMetrics.keymanConnectRate)} sub={`${totalMetrics.connectCount}/${totalMetrics.callCount} 件`} />
        <MetricCard label="受付突破率" value={formatRate(totalMetrics.receptionPassRate)} sub={`受付NG ${totalMetrics.receptionNgCount} 件`} />
        <MetricCard label="次アクション率" value={formatRate(totalMetrics.nextActionRate)} sub={`資料+アポ ${totalMetrics.materialSentCount + totalMetrics.appointmentCount} 件`} />
        <MetricCard label="アポ率" value={formatRate(totalMetrics.appointmentRate)} sub={`アポ ${totalMetrics.appointmentCount} 件`} />
      </div>

      <div className="rounded-xl border border-zinc-200 bg-amber-50 p-4 text-sm text-amber-950">
        <span className="font-semibold">今の見るべき論点: </span>
        {summarizeBottleneck(totalMetrics)}
      </div>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">架電記録（CallLog・直近4週）</h3>
        <p className="text-sm text-zinc-600">
          {callLogSummaryLine.length > 0 ? callLogSummaryLine : 'CallLog はまだありません。'}
        </p>
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                {['日時', '担当', '結果'].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {callLogs.slice(0, 30).map((row) => (
                <tr key={row.id}>
                  <td className="px-3 py-2">{row.startedAt.toISOString().slice(0, 16).replace('T', ' ')}</td>
                  <td className="px-3 py-2">{row.user.name ?? row.user.email ?? '—'}</td>
                  <td className="px-3 py-2">{row.result}</td>
                </tr>
              ))}
              {callLogs.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-zinc-500" colSpan={3}>
                    sales-room から記帳するとここに反映されます。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">週次推移</h3>
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                {['期間', '架電', '接続率', '受付突破', '次アクション', 'アポ率'].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {weeklyMetrics.map((row) => (
                <tr key={row.start.toISOString()}>
                  <td className="px-3 py-2">{toDateInput(row.start)}〜{toDateInput(row.end)}</td>
                  <td className="px-3 py-2">{row.metrics.callCount}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.keymanConnectRate)}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.receptionPassRate)}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.nextActionRate)}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.appointmentRate)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">担当者別（直近4週）</h3>
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                {['担当', '架電', '接続', 'アポ', '接続率', 'アポ率'].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {playerRows.map((row) => (
                <tr key={row.label}>
                  <td className="px-3 py-2">{row.label}</td>
                  <td className="px-3 py-2">{row.metrics.callCount}</td>
                  <td className="px-3 py-2">{row.metrics.connectCount}</td>
                  <td className="px-3 py-2">{row.metrics.appointmentCount}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.keymanConnectRate)}</td>
                  <td className="px-3 py-2">{formatRate(row.metrics.appointmentRate)}</td>
                </tr>
              ))}
              <tr className="bg-zinc-50 font-medium">
                <td className="px-3 py-2">今月合計</td>
                <td className="px-3 py-2">{monthMetrics.callCount}</td>
                <td className="px-3 py-2">{monthMetrics.connectCount}</td>
                <td className="px-3 py-2">{monthMetrics.appointmentCount}</td>
                <td className="px-3 py-2">{formatRate(monthMetrics.keymanConnectRate)}</td>
                <td className="px-3 py-2">{formatRate(monthMetrics.appointmentRate)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-3">
        {[
          ['受付NG理由', topReceptionNgReasons],
          ['キーマンNG理由', topKeymanNgReasons],
          ['アポ獲得要因', topAppointmentReasons]
        ].map(([title, rows]) => (
          <section key={title as string} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-zinc-900">{title as string}</h3>
            <ul className="mt-3 space-y-2 text-sm text-zinc-700">
              {(rows as Array<{ label: string; count: number }>).map((row) => (
                <li key={row.label} className="flex justify-between gap-3">
                  <span>{row.label}</span>
                  <span className="font-medium text-zinc-950">{row.count}</span>
                </li>
              ))}
              {(rows as Array<{ label: string; count: number }>).length === 0 ? (
                <li className="text-zinc-500">未入力</li>
              ) : null}
            </ul>
          </section>
        ))}
      </div>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">時間帯別メモ（最新）</h3>
        <div className="rounded-xl border border-zinc-200 bg-white p-4">
          <ul className="space-y-1 text-sm text-zinc-700">
            {callSlotLines.map((line) => <li key={line}>{line}</li>)}
            {callSlotLines.length === 0 ? <li className="text-zinc-500">未入力</li> : null}
          </ul>
        </div>
      </section>

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">改善示唆ログ</h3>
        <div className="space-y-3">
          {suggestions.map((suggestion) => (
            <article key={suggestion.id} className="rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
              <div className="text-xs text-zinc-500">{suggestion.createdAt.toISOString()}</div>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-800">{suggestion.suggestion}</p>
            </article>
          ))}
          {suggestions.length === 0 ? (
            <p className="rounded-xl border border-zinc-200 bg-white p-4 text-sm text-zinc-500">まだ改善示唆はありません。</p>
          ) : null}
        </div>
      </section>
    </div>
  )
}
