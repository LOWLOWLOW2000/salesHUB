import type { KpiMetrics } from '@/lib/isHub/dailyReport'
import { formatRate, summarizeBottleneck } from '@/lib/isHub/dailyReport'

type SuggestionContext = {
  metrics: KpiMetrics
  topReceptionNgReasons: Array<{ label: string; count: number }>
  topKeymanNgReasons: Array<{ label: string; count: number }>
  topAppointmentReasons: Array<{ label: string; count: number }>
  /** Optional CallLog-derived summary (same period as metrics). */
  callLogSummary?: string
}

export const buildSuggestionPromptSummary = ({
  metrics,
  topReceptionNgReasons,
  topKeymanNgReasons,
  topAppointmentReasons,
  callLogSummary
}: SuggestionContext) =>
  [
    `架電:${metrics.callCount}`,
    `接続:${metrics.connectCount} (${formatRate(metrics.keymanConnectRate)})`,
    `受付突破:${formatRate(metrics.receptionPassRate)}`,
    `次アクション:${formatRate(metrics.nextActionRate)}`,
    `アポ:${metrics.appointmentCount} (${formatRate(metrics.appointmentRate)})`,
    `受付NG上位:${topReceptionNgReasons.map((r) => `${r.label}:${r.count}`).join(', ') || 'なし'}`,
    `キーマンNG上位:${topKeymanNgReasons.map((r) => `${r.label}:${r.count}`).join(', ') || 'なし'}`,
    `アポ要因上位:${topAppointmentReasons.map((r) => `${r.label}:${r.count}`).join(', ') || 'なし'}`,
    callLogSummary && callLogSummary.length > 0 ? `架電記録:${callLogSummary}` : null
  ]
    .filter(Boolean)
    .join('\n')

const buildFallbackSuggestion = (context: SuggestionContext) => {
  const { metrics, topReceptionNgReasons, topKeymanNgReasons, topAppointmentReasons } = context
  const bottleneck = summarizeBottleneck(metrics)
  const reception = topReceptionNgReasons[0]?.label
  const keyman = topKeymanNgReasons[0]?.label
  const win = topAppointmentReasons[0]?.label

  return [
    `ボトルネック: ${bottleneck}`,
    reception ? `受付NGの最多理由は「${reception}」です。呼出し名・部署名・用件の一文を固定し、受付突破用の2回粘りトークを検証してください。` : null,
    keyman ? `キーマンNGの最多理由は「${keyman}」です。切返し後に必ず「一度お時間をいただけませんか？」へ戻す運用を確認してください。` : null,
    win ? `アポ獲得要因は「${win}」が強く出ています。同じ訴求を同業種・同規模リストへ横展開してください。` : null,
    '次の1週間は「時間帯別の接続率」と「アポに至った一言」を日報へ必ず残し、改善判断を感覚ではなく数字で行います。'
  ]
    .filter(Boolean)
    .join('\n')
}

export const buildImprovementSuggestion = async (context: SuggestionContext) => {
  const apiKey = process.env.ANTHROPIC_API_KEY?.trim()
  const promptSummary = buildSuggestionPromptSummary(context)

  if (!apiKey) {
    return {
      promptSummary,
      suggestion: buildFallbackSuggestion(context)
    }
  }

  const res = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01'
    },
    body: JSON.stringify({
      model: process.env.ANTHROPIC_MODEL ?? 'claude-3-5-sonnet-latest',
      max_tokens: 700,
      messages: [
        {
          role: 'user',
          content: `あなたは日本最高水準のインサイドセールス部隊のディレクターです。以下のKPIとNG理由から、次週の改善策を根拠付きで3つ提案してください。\n\n${promptSummary}`
        }
      ]
    })
  })

  if (!res.ok) {
    return {
      promptSummary,
      suggestion: buildFallbackSuggestion(context)
    }
  }

  const data = await res.json()
  const text = data?.content?.[0]?.text

  return {
    promptSummary,
    suggestion: typeof text === 'string' && text.trim().length > 0 ? text.trim() : buildFallbackSuggestion(context)
  }
}
