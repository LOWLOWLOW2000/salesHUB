'use client'

import { useMemo, useState } from 'react'
import { CALLING_RESULT_VALUES } from '@/lib/calling/callResults'
import { saveCallLogAction } from '@/app/sales-room/actions'

export type SalesRoomRow = {
  id: string
  companyName: string
  phone: string
  targetUrl: string
  status: string
}

type Props = {
  projectId: string
  listId: string
  rows: SalesRoomRow[]
}

const sortRows = (rows: SalesRoomRow[]) =>
  [...rows].sort((a, b) => {
    const pri = (s: string) => (s === 'new' ? 0 : 1)
    return pri(a.status) - pri(b.status) || a.companyName.localeCompare(b.companyName, 'ja')
})

const iframeSrc = (url: string) => {
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return `https://${url}`
}

/**
 * Efficient calling workspace: list row, company site iframe, result form.
 */
export const SalesRoomClient = ({ projectId, listId, rows }: Props) => {
  const sorted = useMemo(() => sortRows(rows), [rows])
  const [index, setIndex] = useState(0)
  const current = sorted[index] ?? null
  const [zoomMsg, setZoomMsg] = useState<string | null>(null)

  const openZoom = async () => {
    setZoomMsg(null)
    try {
      const res = await fetch('/api/zoom/dial', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ projectId })
      })
      const json = (await res.json()) as { joinUrl?: string; mode?: string; error?: string }
      if (!res.ok) {
        setZoomMsg(json.error ?? 'zoom failed')
        return
      }
      if (json.joinUrl) window.open(json.joinUrl, '_blank', 'noopener,noreferrer')
      setZoomMsg(json.mode === 'mock' ? 'mock: open Zoom URL from env to go live' : 'opened')
    } catch (e) {
      setZoomMsg(e instanceof Error ? e.message : 'error')
    }
  }

  if (sorted.length === 0) {
    return <p className="text-sm text-zinc-600">このリストに行がありません。CSV をインポートしてください。</p>
  }

  if (!current) return null

  return (
    <div className="grid gap-4 lg:grid-cols-12">
      <aside className="lg:col-span-3">
        <div className="rounded-xl border border-zinc-200 bg-white p-3 text-sm">
          <div className="text-xs font-semibold text-zinc-500">List</div>
          <div className="mt-1 font-mono text-xs text-zinc-600">{listId}</div>
          <div className="mt-3 max-h-[50vh] space-y-1 overflow-y-auto">
            {sorted.map((r, i) => (
              <button
                key={r.id}
                type="button"
                onClick={() => {
                  setIndex(i)
                }}
                className={[
                  'block w-full rounded-lg px-2 py-1.5 text-left text-xs',
                  i === index ? 'bg-zinc-900 text-white' : 'bg-zinc-50 text-zinc-800 hover:bg-zinc-100'
                ].join(' ')}
              >
                <div className="truncate font-medium">{r.companyName}</div>
                <div className="truncate opacity-80">{r.status}</div>
              </button>
            ))}
          </div>
        </div>
      </aside>

      <section className="space-y-3 lg:col-span-5">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void openZoom()}
            className="rounded-lg bg-blue-700 px-3 py-2 text-sm font-medium text-white hover:bg-blue-800"
          >
            Zoom 会議を開く
          </button>
          {zoomMsg ? <span className="text-xs text-zinc-600">{zoomMsg}</span> : null}
        </div>
        <div className="h-[60vh] overflow-hidden rounded-xl border border-zinc-200 bg-white shadow-sm">
          <iframe title="company-site" src={iframeSrc(current.targetUrl)} className="h-full w-full border-0" />
        </div>
      </section>

      <section className="space-y-3 lg:col-span-4">
        <div className="rounded-xl border border-zinc-200 bg-white p-4 text-sm shadow-sm">
          <div className="text-xs font-semibold text-zinc-500">現在の行</div>
          <div className="mt-2 font-semibold text-zinc-950">{current.companyName}</div>
          <div className="mt-1 text-zinc-700">{current.phone}</div>
          <a href={iframeSrc(current.targetUrl)} className="mt-2 block truncate text-xs text-blue-700 hover:underline" target="_blank" rel="noreferrer">
            {current.targetUrl}
          </a>
        </div>

        <form
          action={saveCallLogAction}
          className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm"
        >
          <input type="hidden" name="projectId" value={projectId} />
          <input type="hidden" name="masterListItemId" value={current.id} />
          <label className="block text-sm">
            <span className="font-medium text-zinc-800">結果</span>
            <select
              key={`${current.id}-result`}
              name="result"
              defaultValue={CALLING_RESULT_VALUES[0]}
              className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2"
            >
              {CALLING_RESULT_VALUES.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm">
            <span className="font-medium text-zinc-800">メモ</span>
            <textarea
              key={`${current.id}-memo`}
              name="memo"
              rows={4}
              defaultValue=""
              className="mt-1 w-full rounded-lg border border-zinc-200 px-3 py-2"
            />
          </label>
          <button
            type="submit"
            className="w-full rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            記帳して次へ
          </button>
        </form>

        <a
          className="block text-center text-sm text-zinc-600 underline-offset-2 hover:underline"
          href={`/api/calls/export?projectId=${encodeURIComponent(projectId)}`}
          target="_blank"
          rel="noreferrer"
        >
          この案件の CallLog を CSV ダウンロード
        </a>
      </section>
    </div>
  )
}
