'use client'

import type { DailyReportInput } from '@/lib/isHub/dailyReport'

type Props = {
  action: (formData: FormData) => Promise<void>
  projectId: string
  defaultValues: DailyReportInput
  /** When true, fields and submit are disabled (view-only tier). */
  readOnly?: boolean
}

const numberFields = [
  ['callCount', '架電件数'],
  ['receptionNgCount', '受付NG'],
  ['connectCount', 'キーマン接続'],
  ['keymanNgCount', 'キーマンNG'],
  ['materialSentCount', '資料送付'],
  ['appointmentCount', 'アポ'],
  ['callMinutes', '架電時間（分）'],
  ['totalMinutes', '稼働時間（分）']
] as const

/**
 * 日報入力フォーム。Server Action に送るだけの薄い Client Component。
 */
export const DailyReportForm = ({ action, projectId, defaultValues, readOnly = false }: Props) => {
  return (
    <form action={action} className="space-y-5 rounded-2xl border border-zinc-200 bg-white p-4 shadow-sm">
      <input type="hidden" name="projectId" value={projectId} />

      {readOnly ? (
        <p id="daily-report-readonly-reason" className="text-sm text-zinc-600">
          この案件では閲覧のみのため、日報を保存できません。プロジェクトメンバーに追加してもらってください。
        </p>
      ) : null}

      <fieldset disabled={readOnly} className="min-w-0 space-y-5 border-0 p-0 disabled:opacity-60">
      <div className="grid gap-4 md:grid-cols-3">
        <label className="space-y-1 text-sm">
          <span className="font-medium text-zinc-800">日付</span>
          <input
            name="date"
            type="date"
            required
            defaultValue={defaultValues.date}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </label>

        {numberFields.map(([name, label]) => (
          <label key={name} className="space-y-1 text-sm">
            <span className="font-medium text-zinc-800">{label}</span>
            <input
              name={name}
              type="number"
              min="0"
              step="1"
              defaultValue={defaultValues[name]}
              className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
            />
          </label>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <label className="space-y-1 text-sm">
          <span className="font-medium text-zinc-800">30分枠メモ</span>
          <textarea
            name="callSlots"
            rows={4}
            defaultValue={defaultValues.callSlots}
            placeholder="例: 10:00 架電20 接続4 / 10:30 架電18 接続2"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-zinc-800">受付NG理由</span>
          <textarea
            name="receptionNgReasons"
            rows={4}
            defaultValue={defaultValues.receptionNgReasons}
            placeholder="営業NG, 担当不明, 後日連絡希望 など"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-zinc-800">キーマンNG理由</span>
          <textarea
            name="keymanNgReasons"
            rows={4}
            defaultValue={defaultValues.keymanNgReasons}
            placeholder="ニーズなし, 時期尚早, 他社導入済み など"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </label>

        <label className="space-y-1 text-sm">
          <span className="font-medium text-zinc-800">アポ獲得要因タグ</span>
          <textarea
            name="appointmentReasonTags"
            rows={4}
            defaultValue={defaultValues.appointmentReasonTags}
            placeholder="タイミング合致, 課題訴求, 継続フォロー など"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
          />
        </label>
      </div>

      <label className="space-y-1 text-sm">
        <span className="font-medium text-zinc-800">メモ / 次回施策</span>
        <textarea
          name="notes"
          rows={5}
          defaultValue={defaultValues.notes}
          placeholder="上手くいった施策、受付/キーマンNGの気づき、次回架電への施策"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </label>

      <button
        type="submit"
        aria-describedby={readOnly ? 'daily-report-readonly-reason' : undefined}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        日報を保存
      </button>
      </fieldset>
    </form>
  )
}
