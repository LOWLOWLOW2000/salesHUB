import type { Metadata } from 'next'
import { PdfButton } from '@/components/PdfButton'

export const metadata: Metadata = {
  title: 'KPI'
}

export default function KpiPage() {
  const rates = [
    { label: 'キーマン接続率', value: 'キーマン接続 / 架電件数' },
    { label: '受付突破率', value: '(架電件数 - 受付NG) / 架電件数' },
    { label: '次アクション率', value: '(資料送付 + アポ) / キーマン接続' },
    { label: 'アポ率', value: 'アポ / キーマン接続' }
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">数値設計（KPI定義）</h1>
        <PdfButton path="/docs/kpi" />
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">コアKPI</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-700">
          {['架電件数', '受付NG', 'キーマン接続', 'キーマンNG', '資料送付', 'アポ'].map((k) => (
            <li key={k}>{k}</li>
          ))}
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">派生率（改善の見る順）</h2>
        <ul className="space-y-1 text-sm leading-6 text-zinc-700">
          {rates.map((r) => (
            <li key={r.label} className="flex flex-wrap gap-2">
              <span className="font-medium text-zinc-900">{r.label}</span>
              <span className="text-zinc-600">{r.value}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

