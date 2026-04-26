type Card = {
  title: string
  description: string
}

type Props = {
  cards?: Card[]
}

/**
 * 入口A/B/Cの3カード（同サイズ）
 */
export const CardRowABC = ({
  cards = [
    { title: 'A: 構造最適化', description: '紹介偏重 → 配分の最適化' },
    { title: 'B: 工数', description: '兼務/少人数の巻き取り' },
    { title: 'C: 卒業できるRPO', description: 'ロックイン不満の解消' }
  ]
}: Props) => (
  <div className="grid gap-3 sm:grid-cols-3">
    {cards.map((c) => (
      <div
        key={c.title}
        className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm"
      >
        <div className="text-sm font-semibold text-zinc-900">{c.title}</div>
        <div className="mt-2 text-sm leading-6 text-zinc-600">{c.description}</div>
      </div>
    ))}
  </div>
)

