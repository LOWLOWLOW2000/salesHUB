type Props = {
  title: string
  bullets: string[]
  notes: string[]
}

/**
 * 事例カード（注意書き付き）
 */
export const CaseCard = ({ title, bullets, notes }: Props) => (
  <div className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
    <div className="text-sm font-semibold text-zinc-900">{title}</div>
    <ul className="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-700">
      {bullets.map((b) => (
        <li key={b}>{b}</li>
      ))}
    </ul>
    <div className="mt-4 rounded-lg bg-zinc-50 p-3 text-xs leading-5 text-zinc-600">
      <div className="font-semibold text-zinc-800">注意書き</div>
      <ul className="mt-1 list-disc space-y-1 pl-5">
        {notes.map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
    </div>
  </div>
)

