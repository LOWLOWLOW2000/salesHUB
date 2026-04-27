type Stage = {
  label: string
  subLabel?: string
}

type Props = {
  stages?: Stage[]
}

/**
 * ファネル（Call → Gatekeeper → Keyman → NextAction）
 */
export const Funnel = ({
  stages = [
    { label: 'Call', subLabel: '架電' },
    { label: 'Gatekeeper', subLabel: '受付突破' },
    { label: 'Keyman', subLabel: 'キーマン接続' },
    { label: 'NextAction', subLabel: '資料/アポ' }
  ]
}: Props) => (
  <div className="w-full rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
    <div className="text-sm font-semibold text-zinc-900">Funnel</div>
    <div className="mt-4 grid gap-3 sm:grid-cols-4">
      {stages.map((stage, idx) => (
        <div key={`${stage.label}-${idx}`} className="relative">
          <div className="rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-4">
            <div className="text-xs font-semibold text-zinc-900">{stage.label}</div>
            {stage.subLabel ? (
              <div className="mt-1 text-xs text-zinc-600">{stage.subLabel}</div>
            ) : null}
          </div>
          {idx < stages.length - 1 ? (
            <div className="hidden sm:block">
              <div className="absolute -right-2 top-1/2 h-0.5 w-4 -translate-y-1/2 bg-zinc-300" />
              <div className="absolute -right-3 top-1/2 -translate-y-1/2 text-zinc-400">
                →
              </div>
            </div>
          ) : null}
        </div>
      ))}
    </div>
    <div className="mt-4 text-xs text-zinc-600">
      率は矢印ではなく「段の間」に表示する想定（視線誘導を簡単にする）
    </div>
  </div>
)

