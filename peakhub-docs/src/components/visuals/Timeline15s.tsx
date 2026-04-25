type Segment = {
  from: number
  to: number
  label: string
}

type Props = {
  segments?: Segment[]
}

/**
 * 0–15秒タイムライン（4区間）
 */
export const Timeline15s = ({
  segments = [
    { from: 0, to: 3, label: '謝罪・名乗り' },
    { from: 3, to: 8, label: '要件（採用の構造）' },
    { from: 8, to: 10, label: '15秒許可取り' },
    { from: 10, to: 15, label: '次の一問' }
  ]
}: Props) => (
  <div className="w-full rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
    <div className="flex items-baseline justify-between gap-4">
      <div className="text-sm font-semibold text-zinc-900">Timeline</div>
      <div className="text-xs text-zinc-600">0–15s</div>
    </div>

    <div className="mt-4 overflow-hidden rounded-lg border border-zinc-200">
      <div className="grid grid-cols-4 bg-zinc-50">
        {segments.map((s) => (
          <div key={`${s.from}-${s.to}`} className="border-r border-zinc-200 p-3 last:border-r-0">
            <div className="text-[11px] font-semibold text-zinc-900">
              {s.from}–{s.to}s
            </div>
            <div className="mt-1 text-xs leading-5 text-zinc-600">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  </div>
)

