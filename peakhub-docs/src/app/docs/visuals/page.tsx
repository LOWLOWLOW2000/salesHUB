import type { Metadata } from 'next'
import { PdfButton } from '@/components/PdfButton'
import { Funnel } from '@/components/visuals/Funnel'
import { Timeline15s } from '@/components/visuals/Timeline15s'
import { CardRowABC } from '@/components/visuals/CardRowABC'
import { DecisionFlow } from '@/components/visuals/DecisionFlow'
import { TwoColumnCompare } from '@/components/visuals/TwoColumnCompare'
import { CaseCard } from '@/components/visuals/CaseCard'

export const metadata: Metadata = {
  title: 'Visuals'
}

export default function VisualsPage() {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">インフォグラフィック指示書</h1>
        <PdfButton path="/docs/visuals" />
      </div>

      <section className="space-y-2">
        <h2 className="text-lg font-semibold">共通ルール</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm leading-6 text-zinc-700">
          {[
            '1スライド1メッセージ（文章を増やさない）',
            '余白を大きく、文字は少なめ（箇条書きは最大5行）',
            '数字は盛らない（公式数字・事例のみ使用）',
            '表現ルール: 「削減」ではなく「最適化」、成功率保証NG、独自AI/DB NG'
          ].map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">ファネル</h2>
        <Funnel />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">15秒</h2>
        <Timeline15s />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">3つの入り口</h2>
        <CardRowABC />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">次アクション分岐</h2>
        <DecisionFlow />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">NG→OK置換</h2>
        <TwoColumnCompare
          title="表現ルール"
          leftTitle="NG"
          rightTitle="OK"
          leftTone="danger"
          rightTone="primary"
          rows={[
            { left: 'コスト削減', right: '構造最適化 / 配分最適化' },
            { left: '成功率保証', right: '事例ベースで再現条件を説明' },
            { left: '独自AI/DBを強調', right: '公式に確認できる範囲の表現に限定' }
          ]}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">事例カード</h2>
        <CaseCard
          title="地方中小（製造）"
          bullets={['応募ゼロ → 2ヶ月で2名', '前提: 求人条件・媒体選定・スカウト文面を同時に最適化']}
          notes={['成功率保証の表現はしない', '数字は公式/事例の範囲でのみ使用する']}
        />
      </section>
    </div>
  )
}

