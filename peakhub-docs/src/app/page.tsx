import Link from 'next/link'

export default function Home() {
  return (
    <div className="space-y-8">
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold tracking-tight">PeakHUB 資料</h1>
        <p className="max-w-2xl text-sm leading-6 text-zinc-700">
          「スライド構成」「KPI定義」「インフォグラフィック指示書」を、更新しやすいドキュメントとして運用するためのサイトです。
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        {[
          {
            title: 'Slides',
            href: '/docs/slides',
            description: '20枚のスライド構成（章立て）'
          },
          {
            title: 'KPI',
            href: '/docs/kpi',
            description: '集計定義・派生率・週次レビュー順'
          },
          {
            title: 'Visuals',
            href: '/docs/visuals',
            description: 'ファネル/掛け算/タイムライン等の図解ルール'
          }
        ].map(({ title, href, description }) => (
          <Link
            key={href}
            href={href}
            className="group rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-zinc-300 hover:shadow"
          >
            <div className="text-sm font-semibold">{title}</div>
            <div className="mt-2 text-sm leading-6 text-zinc-600">{description}</div>
            <div className="mt-4 text-xs font-medium text-zinc-500 group-hover:text-zinc-700">
              開く →
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}
