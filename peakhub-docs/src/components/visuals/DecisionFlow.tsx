type Node = {
  label: string
  to?: string[]
}

type Props = {
  title?: string
  nodes?: Node[]
}

/**
 * 分岐フロー（キーマン接続後）
 */
export const DecisionFlow = ({
  title = '分岐フロー',
  nodes = [
    { label: 'キーマン接続後', to: ['興味あり', '今は難しい', '課題不明'] },
    { label: '興味あり', to: ['アポ'] },
    { label: '今は難しい', to: ['資料＋日程'] },
    { label: '課題不明', to: ['追加1問→資料'] }
  ]
}: Props) => (
  <div className="w-full rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
    <div className="text-sm font-semibold text-zinc-900">{title}</div>

    <div className="mt-4 grid gap-3 sm:grid-cols-2">
      {nodes.map((n) => (
        <div key={n.label} className="rounded-lg border border-zinc-200 bg-zinc-50 p-4">
          <div className="text-sm font-semibold text-zinc-900">{n.label}</div>
          {n.to?.length ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {n.to.map((t) => (
                <span
                  key={`${n.label}-${t}`}
                  className="inline-flex items-center rounded-full border border-zinc-200 bg-white px-2 py-0.5 text-xs text-zinc-700"
                >
                  → {t}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ))}
    </div>
  </div>
)

