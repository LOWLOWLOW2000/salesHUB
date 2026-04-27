'use client'

import { useMemo, useState } from 'react'

type Asset = { id: string; name: string; category: string; fileUrl: string }

type Props = {
  assets: Asset[]
  isGm: boolean
}

/**
 * Select materials → CSV download; GM may trigger SMTP summary email (API).
 */
export const MaterialExportPanel = ({ assets, isGm }: Props) => {
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const selectedIds = useMemo(
    () => assets.filter((a) => selected[a.id]).map((a) => a.id),
    [assets, selected]
  )

  const toggle = (id: string) => {
    setSelected((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const downloadCsv = () => {
    if (selectedIds.length === 0) return
    const qs = new URLSearchParams({ ids: selectedIds.join(',') })
    window.open(`/api/materials/export?${qs.toString()}`, '_blank', 'noopener,noreferrer')
  }

  const [to, setTo] = useState('')
  const [accountId, setAccountId] = useState('')
  const [msg, setMsg] = useState<string | null>(null)

  const sendEmail = async () => {
    setMsg(null)
    try {
      const res = await fetch('/api/materials/send-email', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          to,
          accountId,
          assetIds: selectedIds
        })
      })
      const json = (await res.json().catch(() => ({}))) as { ok?: boolean; error?: string }
      if (!res.ok) {
        setMsg(json.error ?? `HTTP ${res.status}`)
        return
      }
      setMsg('sent')
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'failed')
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          onClick={downloadCsv}
          disabled={selectedIds.length === 0}
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          選択を CSV 出力
        </button>
        <span className="self-center text-xs text-zinc-500">{selectedIds.length} 件選択</span>
      </div>

      {isGm ? (
        <div className="space-y-2 rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm">
          <div className="font-semibold text-zinc-900">GM: メール送信（SMTP 設定時）</div>
          <input
            value={to}
            onChange={(e) => setTo(e.target.value)}
            placeholder="to@example.com"
            className="w-full max-w-sm rounded-lg border border-zinc-200 px-3 py-2"
          />
          <input
            value={accountId}
            onChange={(e) => setAccountId(e.target.value)}
            placeholder="SalesAccount id（ログ用）"
            className="w-full max-w-sm rounded-lg border border-zinc-200 px-3 py-2 font-mono text-xs"
          />
          <button
            type="button"
            disabled={selectedIds.length === 0 || to.length === 0 || accountId.length === 0}
            onClick={() => void sendEmail()}
            className="rounded-lg border border-zinc-300 bg-white px-4 py-2 text-sm font-medium text-zinc-800 hover:bg-zinc-100 disabled:opacity-50"
          >
            メール送信
          </button>
          {msg ? <p className="text-xs text-zinc-600">{msg}</p> : null}
        </div>
      ) : null}

      <ul className="divide-y divide-zinc-100 rounded-xl border border-zinc-200 bg-white">
        {assets.map((a) => (
          <li key={a.id} className="flex flex-wrap items-start gap-3 px-4 py-3 text-sm">
            <input type="checkbox" checked={Boolean(selected[a.id])} onChange={() => toggle(a.id)} />
            <div className="min-w-0 flex-1">
              <div className="font-medium text-zinc-900">{a.name}</div>
              <div className="text-xs text-zinc-500">{a.category}</div>
              <a href={a.fileUrl} className="break-all text-xs text-blue-700 hover:underline" target="_blank" rel="noreferrer">
                {a.fileUrl}
              </a>
              <div className="mt-1 font-mono text-[10px] text-zinc-400">{a.id}</div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
