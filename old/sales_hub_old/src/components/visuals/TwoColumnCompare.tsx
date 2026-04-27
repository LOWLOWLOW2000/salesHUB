type Row = {
  left: string
  right: string
}

type Props = {
  title?: string
  leftTitle: string
  rightTitle: string
  rows: Row[]
  leftTone?: 'neutral' | 'danger'
  rightTone?: 'neutral' | 'primary'
}

const tone = {
  left: {
    neutral: 'bg-zinc-50 text-zinc-900',
    danger: 'bg-red-50 text-red-950'
  },
  right: {
    neutral: 'bg-zinc-50 text-zinc-900',
    primary: 'bg-blue-50 text-blue-950'
  }
} as const

/**
 * 2カラム比較（反論→切り返し、NG→OKなど）
 */
export const TwoColumnCompare = ({
  title,
  leftTitle,
  rightTitle,
  rows,
  leftTone = 'neutral',
  rightTone = 'neutral'
}: Props) => (
  <div className="w-full rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
    {title ? <div className="text-sm font-semibold text-zinc-900">{title}</div> : null}

    <div className="mt-4 overflow-hidden rounded-lg border border-zinc-200">
      <div className="grid grid-cols-2 border-b border-zinc-200 text-xs font-semibold">
        <div className={`px-3 py-2 ${tone.left[leftTone]}`}>{leftTitle}</div>
        <div className={`px-3 py-2 ${tone.right[rightTone]}`}>{rightTitle}</div>
      </div>

      <div className="divide-y divide-zinc-200">
        {rows.map((row, idx) => (
          <div key={idx} className="grid grid-cols-2 text-sm">
            <div className="px-3 py-2 text-zinc-900">{row.left}</div>
            <div className="px-3 py-2 text-zinc-900">{row.right}</div>
          </div>
        ))}
      </div>
    </div>
  </div>
)

