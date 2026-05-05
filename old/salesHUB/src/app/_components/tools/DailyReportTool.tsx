import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { prisma } from '@/lib/db/prisma'
import { getSession } from '@/lib/auth/session'
import { canOperateProject } from '@/lib/auth/rbac'
import {
  dailyReportFormSchema,
  parseDateInput,
  todayDateInput,
  toDateInput,
  type DailyReportInput
} from '@/lib/isHub/dailyReport'
import { DailyReportForm } from '@/app/_components/tools/DailyReportForm'

type Props = {
  projectId: string
  canOperate: boolean
  canConfigure: boolean
}

const saveDailyReport = async (formData: FormData) => {
  'use server'

  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const parsed = dailyReportFormSchema.parse(Object.fromEntries(formData))
  const reportDate = parseDateInput(parsed.date)
  const reportId = `${parsed.projectId}:${userId}:${parsed.date}`
  const allowed = await canOperateProject(userId, parsed.projectId)
  if (!allowed) redirect('/')

  await prisma.dailyReport.upsert({
    where: {
      projectId_userId_date: {
        projectId: parsed.projectId,
        userId,
        date: reportDate
      }
    },
    update: {
      callCount: parsed.callCount,
      connectCount: parsed.connectCount,
      receptionNgCount: parsed.receptionNgCount,
      keymanNgCount: parsed.keymanNgCount,
      materialSentCount: parsed.materialSentCount,
      appointmentCount: parsed.appointmentCount,
      callMinutes: parsed.callMinutes,
      totalMinutes: parsed.totalMinutes,
      notes: parsed.notes,
      callSlots: parsed.callSlots,
      receptionNgReasons: parsed.receptionNgReasons,
      keymanNgReasons: parsed.keymanNgReasons,
      appointmentReasonTags: parsed.appointmentReasonTags
    },
    create: {
      id: reportId,
      projectId: parsed.projectId,
      userId,
      date: reportDate,
      callCount: parsed.callCount,
      connectCount: parsed.connectCount,
      receptionNgCount: parsed.receptionNgCount,
      keymanNgCount: parsed.keymanNgCount,
      materialSentCount: parsed.materialSentCount,
      appointmentCount: parsed.appointmentCount,
      callMinutes: parsed.callMinutes,
      totalMinutes: parsed.totalMinutes,
      notes: parsed.notes,
      callSlots: parsed.callSlots,
      receptionNgReasons: parsed.receptionNgReasons,
      keymanNgReasons: parsed.keymanNgReasons,
      appointmentReasonTags: parsed.appointmentReasonTags
    }
  })

  revalidatePath(`/project/${parsed.projectId}`)
}

const emptyDefaults = (projectId: string): DailyReportInput => ({
  projectId,
  date: todayDateInput(),
  callCount: 0,
  connectCount: 0,
  receptionNgCount: 0,
  keymanNgCount: 0,
  materialSentCount: 0,
  appointmentCount: 0,
  callMinutes: 0,
  totalMinutes: 0,
  notes: '',
  callSlots: '',
  receptionNgReasons: '',
  keymanNgReasons: '',
  appointmentReasonTags: ''
})

/**
 * プロジェクトの日報入力と直近日報を表示する Server Component。
 */
export const DailyReportTool = async ({ projectId, canOperate, canConfigure }: Props) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const canViewAll = canConfigure
  const today = parseDateInput(todayDateInput())
  const currentReport = await prisma.dailyReport.findUnique({
    where: {
      projectId_userId_date: {
        projectId,
        userId,
        date: today
      }
    }
  })

  const reports = await prisma.dailyReport.findMany({
    where: {
      projectId,
      ...(canViewAll ? {} : { userId })
    },
    orderBy: { date: 'desc' },
    take: 5,
    select: {
      id: true,
      date: true,
      callCount: true,
      connectCount: true,
      receptionNgCount: true,
      keymanNgCount: true,
      materialSentCount: true,
      appointmentCount: true,
      user: { select: { name: true, email: true } }
    }
  })

  const defaults = currentReport
    ? {
        projectId,
        date: toDateInput(currentReport.date),
        callCount: currentReport.callCount,
        connectCount: currentReport.connectCount,
        receptionNgCount: currentReport.receptionNgCount,
        keymanNgCount: currentReport.keymanNgCount,
        materialSentCount: currentReport.materialSentCount,
        appointmentCount: currentReport.appointmentCount,
        callMinutes: currentReport.callMinutes,
        totalMinutes: currentReport.totalMinutes,
        notes: currentReport.notes,
        callSlots: currentReport.callSlots,
        receptionNgReasons: currentReport.receptionNgReasons,
        keymanNgReasons: currentReport.keymanNgReasons,
        appointmentReasonTags: currentReport.appointmentReasonTags
      }
    : emptyDefaults(projectId)

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-lg font-semibold tracking-tight text-zinc-950">日報（入力）</h2>
        <p className="mt-1 text-sm text-zinc-600">
          架電・接続・NG・アポを同じ粒度で入力し、KPIと改善示唆の元データにします。
        </p>
      </header>

      <DailyReportForm
        action={saveDailyReport}
        projectId={projectId}
        defaultValues={defaults}
        readOnly={!canOperate}
      />

      <section className="space-y-3">
        <h3 className="text-sm font-semibold text-zinc-900">直近の日報</h3>
        <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
          <table className="w-full text-left text-sm">
            <thead className="bg-zinc-50 text-xs text-zinc-600">
              <tr>
                {['日付', '担当', '架電', '接続', '受付NG', 'キーマンNG', '資料', 'アポ'].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {reports.map((report) => (
                <tr key={report.id}>
                  <td className="px-3 py-2">{toDateInput(report.date)}</td>
                  <td className="px-3 py-2">{report.user.name ?? report.user.email ?? 'unknown'}</td>
                  <td className="px-3 py-2">{report.callCount}</td>
                  <td className="px-3 py-2">{report.connectCount}</td>
                  <td className="px-3 py-2">{report.receptionNgCount}</td>
                  <td className="px-3 py-2">{report.keymanNgCount}</td>
                  <td className="px-3 py-2">{report.materialSentCount}</td>
                  <td className="px-3 py-2">{report.appointmentCount}</td>
                </tr>
              ))}
              {reports.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-zinc-500" colSpan={8}>
                    まだ日報がありません。
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
