import type { Metadata } from 'next'
import { PdfButton } from '@/components/PdfButton'

export const metadata: Metadata = {
  title: 'Slides'
}

export default function SlidesPage() {
  const sections = [
    {
      title: '1. 表紙',
      items: [
        'タイトル: コールドコール戦略・戦術（社内報告）',
        '目的: 「キーマン接続→1問→次アクション」最適化'
      ]
    },
    {
      title: '2. 結論（まず何を変えるか）',
      items: ['成果は「リスト品質 × 受付突破 × キーマン15秒 × 次アクション設計」で決まる']
    },
    {
      title: '3. 現状KPI（報告フォーマット準拠）',
      items: ['架電件数／受付NG／キーマン接続／キーマンNG／アポ／資料送付']
    },
    {
      title: '4. 改善ループ（週次）',
      items: ['見る順: キーマン接続率 → 次アクション率 → NG理由上位']
    }
  ]

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">スライド構成</h1>
        <PdfButton path="/docs/slides" />
      </div>

      <div className="space-y-6">
        {sections.map((s) => (
          <section key={s.title} className="space-y-2">
            <h2 className="text-lg font-semibold">{s.title}</h2>
            <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-700">
              {s.items.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  )
}

