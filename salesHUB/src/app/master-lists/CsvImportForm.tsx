'use client'

import { useState } from 'react'

type Props = {
  /** When set, rows append to this list. Otherwise `listName` is required to create a new list. */
  listId?: string
  /** 新規作成時のリストタイプ。省略時は house_list */
  listType?: 'project_sheet' | 'house_list'
}

/**
 * Client-side CSV upload to `/api/lists/import` then reloads on success.
 */
export const CsvImportForm = ({ listId, listType = 'house_list' }: Props) => {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setBusy(true)
    setMessage(null)

    const form = e.currentTarget
    const fd = new FormData(form)

    if (!listId) {
      const name = String(fd.get('listName') ?? '').trim()
      if (name.length === 0) {
        setMessage('listName required')
        setBusy(false)
        return
      }
    }

    try {
      const res = await fetch('/api/lists/import', {
        method: 'POST',
        body: fd
      })
      const json = (await res.json().catch(() => ({}))) as { ok?: boolean; imported?: number; error?: string }

      if (!res.ok) {
        setMessage(json.error ?? `HTTP ${res.status}`)
        return
      }

      setMessage(`Imported ${json.imported ?? 0} rows`)
      const fileInput = form.querySelector('input[name="file"]') as HTMLInputElement | null
      if (fileInput) fileInput.value = ''
      window.location.reload()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="mt-3 space-y-2" onSubmit={(e) => void onSubmit(e)}>
      {listId ? <input type="hidden" name="listId" value={listId} /> : null}
      {!listId ? <input type="hidden" name="listType" value={listType} /> : null}
      {!listId ? (
        <input
          name="listName"
          required
          placeholder="新規リスト名"
          className="w-full max-w-sm rounded-lg border border-zinc-200 px-3 py-2 text-sm"
          disabled={busy}
        />
      ) : null}
      <input name="file" type="file" accept=".csv,text/csv" required className="text-sm" disabled={busy} />
      <button
        type="submit"
        disabled={busy}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
      >
        {busy ? '送信中…' : 'アップロード'}
      </button>
      {message ? <p className="text-xs text-zinc-600">{message}</p> : null}
    </form>
  )
}
